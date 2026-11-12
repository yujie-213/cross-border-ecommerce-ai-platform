from typing import Annotated
from fastapi import Depends, Header, Request
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


class CancelTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expectedRevision: int = Field(ge=1, strict=True)


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
        return error_response(exc.code, status, "Authentication or current authorization rejected")

    @app.exception_handler(TaskError)
    async def task_error(_, exc):
        return error_response(exc.code, exc.status, "Task command could not be completed")

    @app.post("/api/v1/analysis-tasks")
    def create(body: CreateTask, request: Request, actor=Depends(principal),
               key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)] = ...):
        scope = dict(body.scope.model_dump(), tenantId=actor.tenant_id)
        view = request.app.state.tasks.create(actor, key, body.scenarioId, scope, body.parameters, trace_id.get())
        return JSONResponse(view, status_code=202, headers={"Location": "/api/v1/analysis-tasks/" + view["taskRef"]["taskId"]})

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
