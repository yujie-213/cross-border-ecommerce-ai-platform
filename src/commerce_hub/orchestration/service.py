from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
from uuid import uuid4

from sqlalchemy import insert, select, update, func

from commerce_hub.governance.access.service import AccessDenied
from commerce_hub.infrastructure.work import LeaseLost
from .tables import tasks, commands, budgets, reports
from .contracts import DomainResult


class TaskError(RuntimeError):
    def __init__(self, code, status=409):
        self.code, self.status = code, status
        super().__init__(code)


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


class TaskService:
    def __init__(self, engine, access, queue, audit, registry=None, *, deadline_seconds=120, max_attempts=3):
        self.engine, self.access, self.queue, self.audit = engine, access, queue, audit
        self.registry = registry or {}
        self.deadline_seconds, self.max_attempts = deadline_seconds, max_attempts

    @staticmethod
    def fingerprint(value):
        return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

    def create(self, principal, command_key, scenario_id, scope, parameters, trace_id):
        if len(command_key) > 128 or not command_key:
            raise TaskError("INVALID_COMMAND_KEY", 422)
        spec = self.registry.get(scenario_id)
        if not spec:
            raise TaskError("UNSUPPORTED_SCENARIO", 422)
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
            self.access.authorize(conn, principal, "tasks:create", scope)
            existing = conn.execute(select(tasks).where(tasks.c.tenant_id == principal.tenant_id,
                tasks.c.principal_id == principal.principal_id, tasks.c.command_key == command_key).with_for_update()).mappings().first()
            if existing:
                if existing["fingerprint"] != request_fingerprint:
                    raise TaskError("COMMAND_CONFLICT")
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
                "errorCode": row["error_code"], "sourceNature": "SIMULATED_ENGINEERING" if row["scenario_id"].startswith("ENGINEERING_") else "NOT_YET_EVALUATED"}

    def read(self, principal, task_id):
        with self.engine.begin() as conn:
            row = conn.execute(select(tasks).where(tasks.c.tenant_id == principal.tenant_id,
                                                   tasks.c.task_id == task_id)).mappings().first()
            if not row:
                raise TaskError("NOT_FOUND", 404)
            try:
                self.access.authorize(conn, principal, "tasks:read", row["scope"])
            except AccessDenied:
                raise TaskError("NOT_FOUND", 404) from None
            return self._view(conn, row)

    def _view(self, conn, row):
        view = self.view(row)
        report_id = conn.execute(select(reports.c.report_id).filter_by(
            tenant_id=row["tenant_id"], task_id=row["task_id"])).scalar_one_or_none()
        if report_id and row["state"] == "SUCCEEDED":
            view["reportRef"] = {"tenantId": row["tenant_id"], "reportId": report_id}
        return view

    def read_report(self, principal, task_id):
        with self.engine.begin() as conn:
            row = conn.execute(select(tasks).filter_by(tenant_id=principal.tenant_id, task_id=task_id)).mappings().first()
            if not row:
                raise TaskError("NOT_FOUND", 404)
            try:
                self.access.authorize(conn, principal, "tasks:read", row["scope"])
            except AccessDenied:
                raise TaskError("NOT_FOUND", 404) from None
            report = conn.execute(select(reports).filter_by(tenant_id=principal.tenant_id, task_id=task_id)).mappings().first()
            if row["state"] != "SUCCEEDED" or report is None:
                raise TaskError("REPORT_NOT_PUBLISHED", 404)
            # Current G01 scope authorizes the requested fields, not every field
            # of the persisted internal assets. The scenario owns its narrow read DTO.
            spec = self.registry.get(row["scenario_id"])
            if spec is None or spec.version != row["scenario_version"] or not hasattr(spec.handler, "report_view"):
                raise TaskError("NOT_FOUND", 404)
            try:
                if report["payload"].get("scope") != row["scope"]:
                    raise ValueError("REPORT_SCOPE_MISMATCH")
                return spec.handler.report_view(report["payload"])
            except (KeyError, TypeError, ValueError, IndexError):
                raise TaskError("NOT_FOUND", 404) from None

    def cancel(self, principal, task_id, command_key, expected_revision, trace_id):
        fp = self.fingerprint(dict(task=task_id, expectedRevision=expected_revision))
        with self.engine.begin() as conn:
            row = conn.execute(select(tasks).where(tasks.c.tenant_id == principal.tenant_id,
                                                   tasks.c.task_id == task_id)).mappings().first()
            if not row:
                raise TaskError("NOT_FOUND", 404)
            self.access.authorize(conn, principal, "tasks:cancel", row["scope"])
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
        self.access.authorize(conn, principal, "engineering:execute", row["scope"])
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

    def complete(self, lease, principal, plan_version, result=None):
        with self.engine.begin() as conn:
            row = self._execution(conn, lease, principal, plan_version)
            handler = self.registry[row["scenario_id"]].handler
            if hasattr(handler, "validate_result"):
                try:
                    handler.validate_result(result)
                except (ValueError, TypeError):
                    raise TaskError("INVALID_DOMAIN_RESULT") from None
            if result is not None:
                if not isinstance(result, DomainResult) or result.scope != row["scope"]:
                    raise TaskError("INVALID_DOMAIN_RESULT")
                payload = result.model_dump(mode="json")
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
