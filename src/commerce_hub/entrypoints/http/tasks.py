from typing import Annotated
from fastapi import Depends, Header, Request, Query
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse
from commerce_hub.bootstrap.logging import trace_id
from commerce_hub.entrypoints.http.errors import ApiError, error_response
from commerce_hub.governance.access.service import AccessDenied
from commerce_hub.orchestration.service import TaskError


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    storeIds: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(min_length=1, max_length=100)
    warehouseIds: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(min_length=1, max_length=100)
    canonicalSkuIds: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(min_length=1, max_length=100)
    fields: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(min_length=1, max_length=100)


class CreateTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analysisMode: str = Field(pattern="^SINGLE$")
    scenarioId: str = Field(min_length=1, max_length=64)
    scope: Scope
    parameters: dict = Field(default_factory=dict)
    previousReportRef: "ReportRef | None" = None


class ReportRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tenantId: str = Field(min_length=1, max_length=64)
    reportId: str = Field(min_length=1, max_length=64)


CreateTask.model_rebuild()


class CancelTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedRevision: int = Field(ge=1, strict=True)


class ConfirmRequisition(BaseModel):
    model_config = ConfigDict(extra='forbid')
    finalQuantity: int = Field(ge=1, le=100000, strict=True)
    adjustmentReason: str = Field(default='', max_length=1000)


def register_task_routes(app):
    def principal(request: Request):
        service = request.app.state.tasks
        if service is None:
            raise ApiError("IDENTITY_NOT_CONFIGURED", 503, "Trusted identity is not configured")
        authorization = request.headers.get("authorization", "")
        bearer = authorization[7:] if authorization.startswith("Bearer ") else None
        cookie = request.cookies.get("commerce_session")
        if authorization and not bearer or bearer and cookie and bearer != cookie:
            raise AccessDenied("UNAUTHENTICATED")
        actor = service.access.authenticate(bearer or cookie)
        if cookie and request.method not in {"GET", "HEAD", "OPTIONS"}:
            service.access.validate_csrf(actor, request.cookies.get("commerce_csrf"), request.headers.get("x-csrf-token"),
                                         request.headers.get("origin"), request.app.state.settings.browser_origin)
        return actor

    @app.exception_handler(AccessDenied)
    async def access_error(_, exc):
        status = 503 if exc.code == "AUTH_BACKEND_UNAVAILABLE" else 401 if exc.code == "UNAUTHENTICATED" else 403
        response = error_response(exc.code, status, "Authentication or current authorization rejected")
        if status == 401:
            # An invalid HttpOnly cookie cannot be cleared by the browser client.
            # Expire it so a fresh trusted bearer can establish a new session.
            # Authentication still fails; ordinary permission/CSRF denials keep the session.
            response.delete_cookie("commerce_session", secure=True, httponly=True, samesite="strict")
            response.delete_cookie("commerce_csrf", secure=True, samesite="strict")
        return response

    @app.exception_handler(TaskError)
    async def task_error(_, exc):
        return error_response(exc.code, exc.status, "Task command could not be completed")

    @app.post("/api/v1/analysis-tasks")
    def create(body: CreateTask, request: Request, actor=Depends(principal),
               key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)] = ...):
        scope = dict(body.scope.model_dump(), tenantId=actor.tenant_id)
        view = request.app.state.tasks.create(actor, key, body.scenarioId, scope, body.parameters, trace_id.get(),
            previous_report_ref=body.previousReportRef.model_dump() if body.previousReportRef else None)
        return JSONResponse(view, status_code=202, headers={"Location": "/api/v1/analysis-tasks/" + view["taskRef"]["taskId"]})

    @app.get("/api/v1/s01/options")
    def options(request: Request, storeId: str | None = None, warehouseId: str | None = None, canonicalSkuId: str | None = None,
                actor=Depends(principal)):
        service = request.app.state.tasks
        backend = service.registry.get("S01_BACKEND")
        if backend is not None:
            choices = []
            for choice in backend.handler.options(actor.tenant_id):
                scope = choice["scope"]
                if any(value is not None and scope[key] != [value] for key, value in
                    (("storeIds", storeId), ("warehouseIds", warehouseId), ("canonicalSkuIds", canonicalSkuId))):
                    continue
                try:
                    with service.engine.begin() as conn:
                        service.access.authorize(conn, actor, "tasks:create", scope)
                except AccessDenied:
                    continue
                choice['requisitionAllowed'] = False
                if getattr(service, 'requisitions', None) is not None:
                    try:
                        with service.engine.begin() as conn:
                            service.access.authorize(conn, actor, 's01:requisition', scope)
                        choice['requisitionAllowed'] = True
                    except AccessDenied:
                        pass
                choices.append(choice)
            return dict(scenarioId=backend.scenario_id, scenarioVersion=backend.version, analysisMode="SINGLE",
                inputMode="AUTHORIZED_SCOPE" if any(c.get('inputMode') == 'ONLINE_TEACHING_ERP' for c in choices) else "SERVER_PACKAGE_REF", mappedChoices=choices,
                limitations=["HUMAN_CONFIRMED_TEACHING_REQUISITION_ONLY" if any(c.get('requisitionAllowed') for c in choices) else "READONLY_ANALYSIS_ONLY", "SOURCE_AND_RULE_ADMISSION_PER_PACKAGE", "LIVE_AI_EVALUATION_SEPARATE"],
                maxModelCalls=backend.max_calls, actions=["analyze", "read", "cancel"] + (["requisition"] if any(c.get('requisitionAllowed') for c in choices) else []))
        spec = service.registry.get("ENGINEERING_S01_BUSINESS")
        if spec is None or None in (storeId, warehouseId, canonicalSkuId):
            raise TaskError("UNSUPPORTED_SCENARIO", 422)
        scope = dict(tenantId=actor.tenant_id, storeIds=[storeId], warehouseIds=[warehouseId],
                     canonicalSkuIds=[canonicalSkuId], fields=["quantity"])
        with service.engine.begin() as conn:
            service.access.authorize(conn, actor, "tasks:create", scope)
        # Current D02 consumes inline fixed inputs; it has no server-side mapped catalog.
        # Echoing an authorized scope is not proof that any business mapping exists.
        return dict(scenarioId=spec.scenario_id, scenarioVersion=spec.version, analysisMode="SINGLE",
            sourceNature="SIMULATED_ENGINEERING", inputMode="INLINE_ENGINEERING_FIXTURE", scope=scope,
            mappedChoices=[], limitations=["NO_SERVER_SIDE_MAPPED_CATALOG"], realAdmission="BLOCKED",
            aiProvider="MOCK", maxModelCalls=spec.max_calls, actions=["analyze", "read", "cancel"])

    @app.get("/api/v1/analysis-tasks")
    def history(request: Request, storeId: str, warehouseId: str, canonicalSkuId: str,
                scenarioId: str = "S01_BACKEND", limit: int = Query(default=20, ge=1, le=50),
                before: str | None = Query(default=None, max_length=64), actor=Depends(principal)):
        scope = dict(tenantId=actor.tenant_id, storeIds=[storeId], warehouseIds=[warehouseId],
            canonicalSkuIds=[canonicalSkuId], fields=["quantity"])
        return request.app.state.tasks.history(actor, scope, scenario_id=scenarioId, limit=limit, before=before)

    @app.get("/api/v1/analysis-tasks/{task_id}")
    def read(task_id: str, request: Request, actor=Depends(principal)):
        return request.app.state.tasks.read(actor, task_id)

    @app.post("/api/v1/analysis-tasks/{task_id}/cancel")
    def cancel(task_id: str, body: CancelTask, request: Request, actor=Depends(principal),
               key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)] = ...):
        return request.app.state.tasks.cancel(actor, task_id, key, body.expectedRevision, trace_id.get())

    @app.get("/api/v1/analysis-tasks/{task_id}/report")
    def report(task_id: str, request: Request, actor=Depends(principal)):
        return request.app.state.tasks.read_report(actor, task_id)

    def requisition_service(request):
        service = getattr(request.app.state.tasks, 'requisitions', None)
        if service is None:
            raise TaskError('REQUISITION_NOT_ENABLED', 409)
        return service

    @app.post('/api/v1/analysis-tasks/{task_id}/requisition')
    def confirm_requisition(task_id: str, body: ConfirmRequisition, request: Request, actor=Depends(principal),
            key: Annotated[str, Header(alias='Idempotency-Key', min_length=1, max_length=128)] = ...):
        return requisition_service(request).confirm(actor, task_id, key, body.finalQuantity, body.adjustmentReason, trace_id.get())

    @app.get('/api/v1/analysis-tasks/{task_id}/requisition')
    def read_requisition(task_id: str, request: Request, actor=Depends(principal)):
        return requisition_service(request).read(actor, task_id)

    @app.get("/api/v1/analysis-tasks/{task_id}/evidence/{evidence_id}")
    def evidence(task_id: str, evidence_id: str, request: Request, actor=Depends(principal)):
        from commerce_hub.data.evidence import resolve
        value = resolve(request.app.state.tasks.read_report(actor, task_id), evidence_id)
        if value is None:
            raise TaskError("NOT_FOUND", 404)
        return value

    @app.post("/api/v1/session")
    def establish_session(request: Request, actor=Depends(principal)):
        bearer = request.headers.get("authorization", "")
        if not bearer.startswith("Bearer "):
            raise AccessDenied("UNAUTHENTICATED")
        csrf = request.app.state.tasks.access.issue_csrf(actor)
        response = JSONResponse({"principalRef": {"tenantId": actor.tenant_id, "principalId": actor.principal_id}})
        response.set_cookie("commerce_session", bearer[7:], httponly=True, secure=True, samesite="strict", max_age=900)
        response.set_cookie("commerce_csrf", csrf, httponly=False, secure=True, samesite="strict", max_age=900)
        return response

    @app.delete("/api/v1/session")
    def close_session(request: Request, actor=Depends(principal)):
        with request.app.state.database.engine.begin() as conn:
            request.app.state.tasks.access.revoke_token(conn, actor)
        response = JSONResponse({"status": "closed"})
        response.delete_cookie("commerce_session", secure=True, httponly=True, samesite="strict")
        response.delete_cookie("commerce_csrf", secure=True, samesite="strict")
        return response
