from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from uuid import uuid4

from sqlalchemy import insert, select, update, func, or_, and_, cast, literal, JSON

from commerce_hub.governance.access.service import AccessDenied
from commerce_hub.infrastructure.work import LeaseLost
from .tables import tasks, commands, budgets, reports
from .contracts import DomainResult
from .b_authorization import BTaskAuthorization


class TaskError(RuntimeError):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


@dataclass(frozen=True)
class SharedModelAuthorization:
    """One explicit bounded authorization across original tasks, using O01 rows."""
    authorization_id: str
    max_calls: int | None
    max_tokens: int | None
    max_cost: Decimal | None
    max_inflight: int = 1

    def __post_init__(self):
        if (not 1 <= len(self.authorization_id) <= 64
            or self.max_calls is not None and not 1 <= self.max_calls <= 10
            or self.max_tokens is not None and not 1 <= self.max_tokens <= 100000
            or self.max_cost is not None and not Decimal('0') < self.max_cost <= Decimal('1')
            or self.max_inflight != 1):
            raise ValueError('INVALID_SHARED_MODEL_AUTHORIZATION')


@dataclass(frozen=True)
class HandlerSpec:
    scenario_id: str
    version: str
    work_kind: str
    handler: object
    # Caller cannot supply budget or delivery limits. These are trusted assembly policy values.
    max_calls: int = 0
    max_tokens: int = 0
    max_cost: Decimal = Decimal("0")
    policy_version: str = "foundation-disabled-models-v1"
    # Optional for legacy assemblies. New fee-enabled policies bind their unit explicitly.
    cost_currency: str | None = None
    shared_model_authorization: SharedModelAuthorization | None = None
    task_authorization: BTaskAuthorization | None = None

    def __post_init__(self):
        if self.shared_model_authorization and self.policy_version != self.shared_model_authorization.authorization_id:
            raise ValueError('SHARED_AUTHORIZATION_POLICY_MISMATCH')
        if self.task_authorization is not None and not isinstance(self.task_authorization, BTaskAuthorization):
            raise ValueError('INVALID_TASK_AUTHORIZATION')


class TaskService:
    def __init__(self, engine, access, queue, audit, registry=None, *, deadline_seconds=120, max_attempts=3, after_sales_enabled=False):
        self.engine, self.access, self.queue, self.audit = engine, access, queue, audit
        self.registry = registry or {}
        self.deadline_seconds, self.max_attempts = deadline_seconds, max_attempts
        self.after_sales_enabled = after_sales_enabled

    def authorize_task(self, conn, principal, operation, scope, *, spec=None, task=None):
        """One dispatch for create/read/cancel/worker/budget/publication, fail closed for B."""
        if task is not None:
            spec = self.registry.get(task['scenario_id'])
        adapter = spec.task_authorization if spec is not None else None
        b_scope = isinstance(scope, dict) and ('workspaceId' in scope or 'resourceKind' in scope or 'schemaVersion' in scope)
        b_scenario = (task['scenario_id'] if task is not None else spec.scenario_id if spec else '').startswith('B_')
        if b_scope or b_scenario or adapter is not None:
            if (not self.after_sales_enabled or adapter is None
                    or task is not None and spec.version != task['scenario_version']):
                raise AccessDenied()
            return adapter.authorize(self.access, conn, principal, operation, scope)
        legacy = {'create': 'tasks:create', 'read': 'tasks:read', 'cancel': 'tasks:cancel', 'execute': 'engineering:execute'}
        return self.access.authorize(conn, principal, legacy[operation], scope)

    @staticmethod
    def fingerprint(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

    def create(self, principal, command_key, scenario_id, scope, parameters, trace_id, *, previous_report_ref=None):
        if len(command_key) > 128 or not command_key:
            raise TaskError("INVALID_COMMAND_KEY", 422)
        spec = self.registry.get(scenario_id)
        if not spec:
            raise TaskError("UNSUPPORTED_SCENARIO", 422)
        if hasattr(spec.handler, "validate_command"):
            try:
                spec.handler.validate_command(principal, command_key)
            except (ValueError, TypeError):
                raise TaskError("INVALID_COMMAND_KEY", 422) from None
        if "_previousReportRef" in parameters:
            raise TaskError("INVALID_PARAMETERS", 422)
        if previous_report_ref is not None:
            if not hasattr(spec.handler, "bind_previous_report"):
                raise TaskError("UNSUPPORTED_REPORT_RELATION", 422)
            try:
                parameters = spec.handler.bind_previous_report(parameters, previous_report_ref)
            except (ValueError, TypeError):
                raise TaskError("INVALID_PARAMETERS", 422) from None
            if previous_report_ref.get("tenantId") != principal.tenant_id:
                raise TaskError("NOT_FOUND", 404)
        try:
            spec.handler.validate(parameters)
            if hasattr(spec.handler, "validate_scope"):
                spec.handler.validate_scope(parameters, scope)
        except (ValueError, TypeError):
            raise TaskError("INVALID_PARAMETERS", 422) from None
        if len(json.dumps(parameters)) > 16384:
            raise TaskError("PARAMETERS_TOO_LARGE", 422)
        request_fingerprint = self.fingerprint(dict(scenario=scenario_id, scope=scope, parameters=parameters))
        with self.engine.begin() as conn:
            self.authorize_task(conn, principal, 'create', scope, spec=spec)
            if previous_report_ref is not None:
                # A relation never grants access to its target, nor revives a terminal task.
                old = conn.execute(select(tasks).filter_by(tenant_id=principal.tenant_id,
                    task_id=previous_report_ref.get("reportId"))).mappings().first()
                if (previous_report_ref.get("tenantId") != principal.tenant_id or old is None
                        or old["state"] != "SUCCEEDED" or old["scenario_id"] != scenario_id
                        or old["scenario_version"] != spec.version
                        or old["scope"] != scope):
                    raise TaskError("NOT_FOUND", 404)
                try:
                    self.authorize_task(conn, principal, 'read', old['scope'], task=old)
                except AccessDenied:
                    raise TaskError("NOT_FOUND", 404) from None
                published = conn.execute(select(reports).filter_by(
                    tenant_id=principal.tenant_id, task_id=old["task_id"],
                    report_id=previous_report_ref["reportId"])).mappings().first()
                if published is None:
                    raise TaskError("NOT_FOUND", 404)
                self._validate_report_row(conn, old, published)
            existing = conn.execute(select(tasks).where(tasks.c.tenant_id == principal.tenant_id,
                tasks.c.principal_id == principal.principal_id, tasks.c.command_key == command_key).with_for_update()).mappings().first()
            if existing:
                if existing["fingerprint"] != request_fingerprint:
                    raise TaskError("COMMAND_CONFLICT")
                if spec.task_authorization is not None:
                    self.authorize_task(conn, principal, 'read', existing['scope'], task=existing)
                return self._view(conn, existing)
            now = conn.scalar(select(func.utc_timestamp(6)))
            task_id, work_id = uuid4().hex, uuid4().hex
            values = dict(tenant_id=principal.tenant_id, task_id=task_id, principal_id=principal.principal_id,
                principal_revision=principal.revision, token_id=principal.token_id,
                command_key=command_key, fingerprint=request_fingerprint, scenario_id=scenario_id,
                scenario_version=spec.version, plan_version=1, scope=scope, parameters=parameters,
                state="QUEUED", revision=1, work_id=work_id, created_at=now,
                deadline=now + timedelta(seconds=self.deadline_seconds), error_code=None)
            conn.execute(insert(tasks).values(**values))
            conn.execute(insert(budgets).values(tenant_id=principal.tenant_id, task_id=task_id,
                policy_version=spec.policy_version, max_calls=spec.max_calls, max_tokens=spec.max_tokens,
                max_cost=spec.max_cost, used_calls=0, used_tokens=0, used_cost=0,
                reserved_calls=0, reserved_tokens=0, reserved_cost=0))
            self.queue.enqueue(conn, tenant_id=principal.tenant_id, work_id=work_id, owner_id=task_id,
                               kind=spec.work_kind, max_attempts=self.max_attempts)
            self.audit.record(conn, tenant_id=principal.tenant_id, principal_id=principal.principal_id,
                              task_id=task_id, action="TASK_CREATED", trace_id=trace_id)
            return self.view(values)

    @staticmethod
    def view(row):
        return {"taskRef": {"tenantId": row["tenant_id"], "taskId": row["task_id"]}, "state": row["state"],
                "revision": row["revision"], "planVersion": str(row["plan_version"]), "reportRef": None,
                "scenarioId": row["scenario_id"], "deadline": row["deadline"].isoformat() + "Z",
                "createdAt": row["created_at"].isoformat() + "Z",
                "errorCode": row["error_code"], "sourceNature": "SIMULATED_ENGINEERING" if row["scenario_id"].startswith("ENGINEERING_") else "NOT_YET_EVALUATED"}

    def read(self, principal, task_id):
        with self.engine.begin() as conn:
            row = conn.execute(select(tasks).where(tasks.c.tenant_id == principal.tenant_id,
                                                   tasks.c.task_id == task_id)).mappings().first()
            if not row:
                raise TaskError("NOT_FOUND", 404)
            try:
                self.authorize_task(conn, principal, 'read', row['scope'], task=row)
            except AccessDenied:
                raise TaskError("NOT_FOUND", 404) from None
            return self._view(conn, row)

    def find_command(self,principal,command_key):
        """Current authorized lookup; does not retry or create an asynchronous job."""
        with self.engine.begin() as conn:
            self.access._assert_current(conn,principal,lock=True)
            row=conn.execute(select(tasks).filter_by(tenant_id=principal.tenant_id,principal_id=principal.principal_id,command_key=command_key)).mappings().first()
            if row is None:raise TaskError('COMMAND_NOT_FOUND',404)
            self.authorize_task(conn,principal,'read',row['scope'],task=row)
            return dict(status='FOUND',result=self._view(conn,row))

    def history(self, principal, scope, *, scenario_id="S01_BACKEND", limit=20, before=None):
        """Bounded, currently authorized task/report index; no parameters or assets."""
        if type(limit) is not int or not 1 <= limit <= 50 or scenario_id not in self.registry:
            raise TaskError("INVALID_HISTORY_QUERY", 422)
        with self.engine.begin() as conn:
            self.authorize_task(conn, principal, 'read', scope, spec=self.registry[scenario_id])
            # MySQL must compare JSON objects, not a JSON column to serialized text.
            scope_match = tasks.c.scope == cast(literal(scope, type_=JSON), JSON)
            query = select(tasks).where(tasks.c.tenant_id == principal.tenant_id,
                tasks.c.scenario_id == scenario_id, scope_match)
            if before is not None:
                anchor = conn.execute(select(tasks).filter_by(tenant_id=principal.tenant_id,
                    task_id=before, scenario_id=scenario_id).where(scope_match)).mappings().first()
                if anchor is None:
                    raise TaskError("NOT_FOUND", 404)
                query = query.where(or_(tasks.c.created_at < anchor["created_at"],
                    and_(tasks.c.created_at == anchor["created_at"], tasks.c.task_id < anchor["task_id"])))
            rows = conn.execute(query.order_by(tasks.c.created_at.desc(), tasks.c.task_id.desc()).limit(limit + 1)).mappings().all()
            visible = []
            for row in rows[:limit]:
                try:
                    self.authorize_task(conn, principal, 'read', row['scope'], task=row)
                    visible.append(self._view(conn, row))
                except AccessDenied as exc:
                    if exc.code == 'AUTH_BACKEND_UNAVAILABLE':
                        raise
            return dict(items=visible,
                nextCursor=rows[limit-1]["task_id"] if len(rows) > limit else None)

    def mixed_history(self, principal, *, limit=20, before=None, workspace_id=None):
        """Bounded mixed index, each row checked with its persisted scenario and scope.

        The signed scan position carries a digest rather than an unauthorized task ID.
        An empty page can still have a cursor when a bounded scan contained hidden rows.
        """
        import hmac
        if type(limit) is not int or not 1 <= limit <= 50:
            raise TaskError('INVALID_HISTORY_QUERY', 422)
        from commerce_hub.governance.access.b_resources import identifier
        if workspace_id is not None and (not identifier(workspace_id) or len(workspace_id) > 64):
            raise TaskError('INVALID_HISTORY_QUERY', 422)
        # AccessControl owns signing; no session secrets enter cursors or response DTOs.
        with self.engine.begin() as conn:
            self.access._assert_current(conn, principal, lock=True)
            query = select(tasks).where(tasks.c.tenant_id == principal.tenant_id)
            if before:
                try:
                    import base64
                    raw, signature = before.split('.')
                    expected = self.access.sign_task_cursor(principal, raw, workspace_id)
                    if not hmac.compare_digest(signature, expected):
                        raise ValueError()
                    anchor = json.loads(base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)))
                    from datetime import datetime
                    date, task_digest = datetime.fromisoformat(anchor[0]), anchor[1]
                    import re
                    if not isinstance(task_digest, str) or not re.fullmatch('[0-9a-f]{64}', task_digest):
                        raise ValueError()
                    task_id = conn.execute(select(tasks.c.task_id).where(tasks.c.tenant_id == principal.tenant_id,
                        tasks.c.created_at == date, func.sha2(tasks.c.task_id, 256) == task_digest)).scalar_one_or_none()
                    if task_id is None:
                        raise ValueError()
                    query = query.where(or_(tasks.c.created_at < date,
                        and_(tasks.c.created_at == date, tasks.c.task_id < task_id)))
                except (ValueError, TypeError, IndexError, KeyError):
                    raise TaskError('INVALID_HISTORY_QUERY', 422) from None
            rows = conn.execute(query.order_by(tasks.c.created_at.desc(), tasks.c.task_id.desc()).limit(201)).mappings().all()
            items, scanned = [], None
            for row in rows[:200]:
                scanned = row
                if workspace_id is not None and row['scope'].get('workspaceId') != workspace_id:
                    continue
                try:
                    self.authorize_task(conn, principal, 'read', row['scope'], task=row)
                except AccessDenied as exc:
                    if exc.code == 'AUTH_BACKEND_UNAVAILABLE':
                        raise
                    continue
                items.append(self._view(conn, row))
                if len(items) == limit:
                    break
            cursor = None
            if scanned is not None and (scanned != rows[-1] or len(rows) > 200):
                import base64
                raw = base64.urlsafe_b64encode(json.dumps([scanned['created_at'].isoformat(), hashlib.sha256(scanned['task_id'].encode()).hexdigest()]).encode()).decode().rstrip('=')
                cursor = raw + '.' + self.access.sign_task_cursor(principal, raw, workspace_id)
            return dict(items=items, nextCursor=cursor)

    def _view(self, conn, row):
        view = self.view(row)
        report_id = conn.execute(select(reports.c.report_id).filter_by(
            tenant_id=row["tenant_id"], task_id=row["task_id"])).scalar_one_or_none()
        if report_id and row["state"] == "SUCCEEDED":
            view["reportRef"] = {"tenantId": row["tenant_id"], "reportId": report_id}
        return view

    def _validate_report_row(self, conn, task, report):
        """Bind persisted payload to its owning SQL rows before linking or exposing it."""
        payload = report["payload"]
        try:
            valid = (report["tenant_id"] == task["tenant_id"] and report["task_id"] == task["task_id"]
                and report["plan_version"] == task["plan_version"]
                and report["fingerprint"] == self.fingerprint(payload)
                and payload["taskRef"] == {"tenantId": task["tenant_id"], "taskId": task["task_id"]}
                and payload["reportRef"] == {"tenantId": task["tenant_id"], "reportId": report["report_id"]}
                and payload["planVersion"] == str(task["plan_version"])
                and payload["scenarioId"] == task["scenario_id"]
                and payload["scenarioVersion"] == task["scenario_version"]
                and payload["scope"] == task["scope"])
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            raise TaskError("NOT_FOUND", 404)
        spec = self.registry.get(task["scenario_id"])
        if spec is not None and hasattr(spec.handler, "validate_report_parameters"):
            try:
                spec.handler.validate_report_parameters(payload, task["parameters"])
            except (KeyError, TypeError, ValueError, IndexError):
                raise TaskError("NOT_FOUND", 404) from None
        if spec is not None and hasattr(spec.handler, "model_receipts"):
            try:
                for receipt in spec.handler.model_receipts(payload):
                    self.audit.verify_model_receipt(conn, tenant_id=task["tenant_id"], task_id=task["task_id"], receipt=receipt)
            except (KeyError, TypeError, ValueError):
                raise TaskError("NOT_FOUND", 404) from None

    def read_report(self, principal, task_id):
        with self.engine.begin() as conn:
            row = conn.execute(select(tasks).filter_by(tenant_id=principal.tenant_id, task_id=task_id)).mappings().first()
            if not row:
                raise TaskError("NOT_FOUND", 404)
            try:
                self.authorize_task(conn, principal, 'read', row['scope'], task=row)
            except AccessDenied:
                raise TaskError("NOT_FOUND", 404) from None
            report = conn.execute(select(reports).filter_by(tenant_id=principal.tenant_id, task_id=task_id)).mappings().first()
            if row["state"] != "SUCCEEDED" or report is None:
                raise TaskError("REPORT_NOT_PUBLISHED", 404)
            self._validate_report_row(conn, row, report)
            # Current G01 scope authorizes the requested fields, not every field
            # of the persisted internal assets. The scenario owns its narrow read DTO.
            spec = self.registry.get(row["scenario_id"])
            if spec is None or spec.version != row["scenario_version"] or not hasattr(spec.handler, "report_view"):
                raise TaskError("NOT_FOUND", 404)
            try:
                if report["payload"].get("scope") != row["scope"]:
                    raise ValueError("REPORT_SCOPE_MISMATCH")
                view=getattr(spec.handler,'authorized_report_view',None)
                if view is None:return spec.handler.report_view(report["payload"])
                payload=report['payload']
            except (KeyError, TypeError, ValueError, IndexError):
                raise TaskError("NOT_FOUND", 404) from None
        # The scenario may reauthorize related B assets on its own connection.
        # Release O01's principal lock first; nested lock-owning connections
        # would otherwise wait on this very request and stall other sessions.
        try:return view(payload,principal)
        except (KeyError,TypeError,ValueError,IndexError):raise TaskError('NOT_FOUND',404) from None

    def cancel(self, principal, task_id, command_key, expected_revision, trace_id):
        fp = self.fingerprint(dict(task=task_id, expectedRevision=expected_revision))
        with self.engine.begin() as conn:
            row = conn.execute(select(tasks).where(tasks.c.tenant_id == principal.tenant_id,
                                                   tasks.c.task_id == task_id)).mappings().first()
            if not row:
                raise TaskError("NOT_FOUND", 404)
            self.authorize_task(conn, principal, 'cancel', row['scope'], task=row)
            row = conn.execute(select(tasks).where(tasks.c.tenant_id == principal.tenant_id,
                tasks.c.task_id == task_id).with_for_update()).mappings().one()
            key = dict(tenant_id=principal.tenant_id, principal_id=principal.principal_id, command_key=command_key)
            previous = conn.execute(select(commands).filter_by(**key)).mappings().first()
            if previous:
                if previous["fingerprint"] != fp:
                    raise TaskError("COMMAND_CONFLICT")
                return self.view(row)
            if row["revision"] != expected_revision:
                raise TaskError("REVISION_CONFLICT")
            if row["state"] not in ["QUEUED", "RUNNING", "CANCELLED"]:
                raise TaskError("TASK_TERMINAL")
            revision = row["revision"] + (row["state"] != "CANCELLED")
            conn.execute(update(tasks).filter_by(tenant_id=principal.tenant_id, task_id=task_id)
                         .values(state="CANCELLED", revision=revision, error_code="CANCELLED"))
            self.queue.cancel(conn, principal.tenant_id, row["work_id"])
            conn.execute(insert(commands).values(**key, fingerprint=fp, task_id=task_id, revision=revision))
            self.audit.record(conn, tenant_id=principal.tenant_id, principal_id=principal.principal_id,
                              task_id=task_id, action="TASK_CANCELLED", trace_id=trace_id)
            return self.view(dict(row, state="CANCELLED", revision=revision, error_code="CANCELLED"))

    def _execution(self, conn, lease, principal, plan_version):
        row = conn.execute(select(tasks).where(tasks.c.tenant_id == lease.tenant_id,
                                               tasks.c.task_id == lease.owner_id)).mappings().first()
        if not row:
            raise TaskError("NOT_FOUND", 404)
        self.authorize_task(conn, principal, 'execute', row['scope'], task=row)
        row = conn.execute(select(tasks).where(tasks.c.tenant_id == lease.tenant_id,
            tasks.c.task_id == lease.owner_id).with_for_update()).mappings().one()
        self.queue.validate(conn, lease)
        if row["plan_version"] != plan_version:
            raise TaskError("STALE_PLAN")
        if row["state"] not in ["QUEUED", "RUNNING"]:
            raise TaskError("TASK_STOPPED")
        if row["deadline"] <= conn.scalar(select(func.utc_timestamp(6))):
            raise TaskError("DEADLINE_EXCEEDED")
        return row

    def start(self, lease, principal):
        with self.engine.begin() as conn:
            row = self._execution(conn, lease, principal, lease.owner_version)
            conn.execute(update(tasks).filter_by(tenant_id=lease.tenant_id, task_id=lease.owner_id)
                         .values(state="RUNNING", revision=tasks.c.revision + 1))
            return dict(row)

    def checkpoint(self, lease, principal, plan_version):
        with self.engine.begin() as conn:
            self._execution(conn, lease, principal, plan_version)

    def execution_transaction(self, lease, principal, plan_version, operation):
        """Coordinate a data owner's short commit with current execution authority.

        The callback must be local DB work; network IO remains outside this transaction.
        Data owners retain their own tables and contracts.
        """
        with self.engine.begin() as conn:
            self._execution(conn, lease, principal, plan_version)
            return operation(conn)

    def complete(self, lease, principal, plan_version, result=None):
        with self.engine.begin() as conn:
            row = self._execution(conn, lease, principal, plan_version)
            handler = self.registry[row["scenario_id"]].handler
            if hasattr(handler, "validate_result"):
                try:
                    handler.validate_result(result)
                except (ValueError, TypeError):
                    raise TaskError("INVALID_DOMAIN_RESULT") from None
            if hasattr(handler, "validate_publication"):
                try:
                    handler.validate_publication(result,
                        {"tenantId": lease.tenant_id, "taskId": lease.owner_id}, str(plan_version))
                except (ValueError, TypeError):
                    raise TaskError("INVALID_DOMAIN_RESULT") from None
            if result is not None:
                if not isinstance(result, DomainResult) or result.scope != row["scope"]:
                    raise TaskError("INVALID_DOMAIN_RESULT")
                payload = result.model_dump(mode="json")
                if hasattr(handler, "validate_report_parameters"):
                    try:
                        handler.validate_report_parameters(payload, row["parameters"])
                    except (KeyError, TypeError, ValueError, IndexError):
                        raise TaskError("INVALID_DOMAIN_RESULT") from None
                if hasattr(handler, "model_receipts"):
                    try:
                        for receipt in handler.model_receipts(payload):
                            self.audit.verify_model_receipt(conn, tenant_id=lease.tenant_id, task_id=lease.owner_id, receipt=receipt)
                    except (KeyError, TypeError, ValueError):
                        raise TaskError("INVALID_DOMAIN_RESULT") from None
                if len(json.dumps(payload)) > 262144:
                    raise TaskError("REPORT_TOO_LARGE")
                payload.update(taskRef={"tenantId": lease.tenant_id, "taskId": lease.owner_id},
                    reportRef={"tenantId": lease.tenant_id, "reportId": lease.owner_id},
                    planVersion=str(plan_version), scenarioId=row["scenario_id"], scenarioVersion=row["scenario_version"],
                    participants=[dict(scenarioId=row["scenario_id"], snapshotRef=result.snapshotRef)])
                conn.execute(insert(reports).values(tenant_id=lease.tenant_id, task_id=lease.owner_id,
                    report_id=lease.owner_id, plan_version=plan_version, fingerprint=self.fingerprint(payload),
                    payload=payload, created_at=func.utc_timestamp(6)))
                self.audit.record(conn, tenant_id=lease.tenant_id, principal_id=row["principal_id"],
                    task_id=lease.owner_id, action="REPORT_PUBLISHED", details={"planVersion": plan_version})
            conn.execute(update(tasks).filter_by(tenant_id=lease.tenant_id, task_id=lease.owner_id)
                         .values(state="SUCCEEDED", revision=row["revision"] + 1))
            self.audit.record(conn, tenant_id=lease.tenant_id, principal_id=row["principal_id"],
                              task_id=lease.owner_id, action="TASK_COMPLETED", details={"planVersion": plan_version})
            self.queue.finish(conn, lease)

    def fail(self, lease, code, *, retryable=False, plan_version=None):
        plan_version = lease.owner_version if plan_version is None else plan_version
        with self.engine.begin() as conn:
            row = conn.execute(select(tasks).where(tasks.c.tenant_id == lease.tenant_id,
                tasks.c.task_id == lease.owner_id).with_for_update()).mappings().first()
            if not row or row["state"] in ["SUCCEEDED", "CANCELLED", "FAILED"] or row["plan_version"] != plan_version:
                return
            work = self.queue.validate(conn, lease)
            now = conn.scalar(select(func.utc_timestamp(6)))
            retry = retryable and work["attempt"] < work["max_attempts"] and row["deadline"] > now
            conn.execute(update(tasks).filter_by(tenant_id=lease.tenant_id, task_id=lease.owner_id)
                         .values(state="QUEUED" if retry else "FAILED", error_code=code, revision=row["revision"] + 1))
            self.queue.finish(conn, lease, "RETRY_WAIT" if retry else "DEAD", delay=0.1 if retry else 0)
            self.audit.record(conn, tenant_id=lease.tenant_id, principal_id=row["principal_id"],
                              task_id=lease.owner_id, action="TASK_RETRY" if retry else "TASK_FAILED", code=code)

    def reconcile_dead(self):
        for tenant_id, task_id, work_id, owner_version in self.queue.terminal_owners([spec.work_kind for spec in self.registry.values()]):
            with self.engine.begin() as conn:
                row = conn.execute(select(tasks).filter_by(tenant_id=tenant_id, task_id=task_id)
                                   .with_for_update()).mappings().first()
                if (row and row["state"] in ["RUNNING", "QUEUED"] and row["plan_version"] == owner_version
                    and row["work_id"] == work_id):
                    conn.execute(update(tasks).filter_by(tenant_id=tenant_id, task_id=task_id)
                        .values(state="FAILED", error_code="DELIVERY_EXHAUSTED", revision=row["revision"] + 1))
                    self.audit.record(conn, tenant_id=tenant_id, principal_id=row["principal_id"],
                                      task_id=task_id, action="TASK_FAILED", code="DELIVERY_EXHAUSTED")
