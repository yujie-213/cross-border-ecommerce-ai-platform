"""O01 original-task allowance control. G02 owns actual usage facts."""
from decimal import Decimal, InvalidOperation
from datetime import timezone

from sqlalchemy import insert, select, update, func

from .tables import budgets, attempts


class BudgetError(RuntimeError):
    pass


def amount(value):
    try:
        result = Decimal(value)
        if not result.is_finite() or result < 0 or result > Decimal("999999999999.99999999") or result != result.quantize(Decimal("0.00000001")):
            raise ValueError()
        return result
    except (ValueError, TypeError, InvalidOperation):
        raise BudgetError("INVALID_COST") from None


class TaskBudgetHandle:
    def __init__(self, service, lease, principal, plan_version):
        self.service, self.lease, self.principal, self.plan_version = service, lease, principal, plan_version

    def _key(self, attempt_id):
        if not isinstance(attempt_id, str) or not 1 <= len(attempt_id) <= 64:
            raise BudgetError("INVALID_ATTEMPT")
        return dict(tenant_id=self.lease.tenant_id, task_id=self.lease.owner_id, attempt_id=attempt_id)

    def validate_model_call(self, *, task_ref, principal_ref, plan_version, policy_ref,
                            attempt_id, logical_call_id, allowance_ref, deadline):
        """Public O01 binding read; current authority/lease and original deadline are authoritative."""
        key = self._key(attempt_id)
        if (task_ref != {"tenantId": key["tenant_id"], "taskId": key["task_id"]} or
            principal_ref != {"tenantId": self.principal.tenant_id, "principalId": self.principal.principal_id} or
            plan_version != str(self.plan_version) or
            allowance_ref != {"tenantId": key["tenant_id"], "id": attempt_id, "version": "1"}):
            raise BudgetError("MODEL_BINDING_DENIED")
        with self.service.engine.begin() as conn:
            task = self.service._execution(conn, self.lease, self.principal, self.plan_version)
            budget = conn.execute(select(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"])).mappings().one()
            row = conn.execute(select(attempts).filter_by(**key)).mappings().first()
            if (policy_ref != {"id": budget["policy_version"], "version": "1"} or not row or
                row["logical_call_id"] != logical_call_id or deadline > task["deadline"].replace(tzinfo=timezone.utc)):
                raise BudgetError("MODEL_BINDING_DENIED")
            now = conn.scalar(select(func.utc_timestamp(6))).replace(tzinfo=timezone.utc)
            if deadline <= now:
                raise BudgetError("DEADLINE_EXCEEDED")
            return dict(state=row["state"], max_tokens=row["max_tokens"], max_cost=row["max_cost"], now=now)

    def send_model(self, attempt_id, logical_call_id, *, max_inflight, details, trace_id):
        """Serialize send admission across processes using the existing task budget row."""
        key = self._key(attempt_id)
        if type(max_inflight) is not int or not 1 <= max_inflight <= 4:
            raise BudgetError("INVALID_CONCURRENCY")
        with self.service.engine.begin() as conn:
            self.service._execution(conn, self.lease, self.principal, self.plan_version)
            conn.execute(select(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"]).with_for_update()).one()
            row = conn.execute(select(attempts).filter_by(**key).with_for_update()).mappings().one()
            if row["state"] != "RESERVED" or row["logical_call_id"] != logical_call_id:
                raise BudgetError("ATTEMPT_NOT_SENDABLE")
            pending = conn.execute(select(attempts.c.logical_call_id, attempts.c.state).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"])
                .where(attempts.c.state.in_(["SENT", "UNKNOWN"]))).all()
            if logical_call_id in [p.logical_call_id for p in pending] or any(p.state == "UNKNOWN" for p in pending):
                raise BudgetError("USAGE_MUST_BE_RECONCILED")
            if len(pending) >= max_inflight:
                raise BudgetError("CONCURRENCY_DENIED")
            self.service.audit.record(conn, tenant_id=key["tenant_id"], task_id=key["task_id"],
                principal_id=self.principal.principal_id, action="MODEL_SENT", trace_id=trace_id, details=details)
            conn.execute(update(attempts).filter_by(**key).values(state="SENT"))

    def model_event(self, *, code, details, trace_id):
        """Late technical facts may be recorded after cancellation; this never authorizes a send."""
        with self.service.engine.begin() as conn:
            return self.service.audit.record(conn, tenant_id=self.lease.tenant_id, task_id=self.lease.owner_id,
                principal_id=self.principal.principal_id, action="MODEL_RESULT", code=code,
                details=details, trace_id=trace_id)

    def reserve(self, logical_call_id, attempt_id, tokens, cost):
        upper = amount(cost)
        if type(tokens) is not int or not 0 <= tokens <= 2147483647 or not isinstance(logical_call_id, str) or not 1 <= len(logical_call_id) <= 64:
            raise BudgetError("INVALID_ALLOWANCE")
        key = self._key(attempt_id)
        with self.service.engine.begin() as conn:
            self.service._execution(conn, self.lease, self.principal, self.plan_version)
            budget = conn.execute(select(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"])
                                  .with_for_update()).mappings().one()
            old = conn.execute(select(attempts).filter_by(**key)).mappings().first()
            if old:
                if (old["logical_call_id"], old["max_tokens"], old["max_cost"]) != (logical_call_id, tokens, upper):
                    raise BudgetError("ATTEMPT_CONFLICT")
                return dict(allowanceRef={"tenantId": key["tenant_id"], "id": attempt_id, "version": "1"}, state=old["state"])
            unresolved = conn.execute(select(attempts.c.attempt_id).filter_by(tenant_id=key["tenant_id"],
                task_id=key["task_id"], logical_call_id=logical_call_id)
                .where(attempts.c.state.in_(["SENT", "UNKNOWN"]))).first()
            if unresolved:
                raise BudgetError("USAGE_MUST_BE_RECONCILED")
            if (budget["used_calls"] + budget["reserved_calls"] + 1 > budget["max_calls"] or
                budget["used_tokens"] + budget["reserved_tokens"] + tokens > budget["max_tokens"] or
                budget["used_cost"] + budget["reserved_cost"] + upper > budget["max_cost"]):
                raise BudgetError("BUDGET_DENIED")
            conn.execute(insert(attempts).values(**key, logical_call_id=logical_call_id, state="RESERVED", max_tokens=tokens, max_cost=upper))
            conn.execute(update(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"])
                .values(reserved_calls=budgets.c.reserved_calls + 1, reserved_tokens=budgets.c.reserved_tokens + tokens,
                        reserved_cost=budgets.c.reserved_cost + upper))
            return dict(allowanceRef={"tenantId": key["tenant_id"], "id": attempt_id, "version": "1"}, state="RESERVED")

    def mark_sent(self, attempt_id):
        key = self._key(attempt_id)
        with self.service.engine.begin() as conn:
            self.service._execution(conn, self.lease, self.principal, self.plan_version)
            row = conn.execute(select(attempts).filter_by(**key).with_for_update()).mappings().first()
            if not row or row["state"] != "RESERVED":
                raise BudgetError("ATTEMPT_NOT_SENDABLE")
            conn.execute(update(attempts).filter_by(**key).values(state="SENT"))

    def unknown(self, attempt_id):
        with self.service.engine.begin() as conn:
            conn.execute(update(attempts).filter_by(**self._key(attempt_id))
                .where(attempts.c.state.in_(["SENT", "RESERVED"])).values(state="UNKNOWN"))

    def release_unsent(self, attempt_id):
        key = self._key(attempt_id)
        with self.service.engine.begin() as conn:
            conn.execute(select(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"]).with_for_update()).one()
            row = conn.execute(select(attempts).filter_by(**key).with_for_update()).mappings().one()
            if row["state"] == "RELEASED":
                return
            if row["state"] != "RESERVED":
                raise BudgetError("USAGE_MUST_BE_RECONCILED")
            conn.execute(update(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"])
                .values(reserved_calls=budgets.c.reserved_calls - 1, reserved_tokens=budgets.c.reserved_tokens - row["max_tokens"],
                        reserved_cost=budgets.c.reserved_cost - row["max_cost"]))
            conn.execute(update(attempts).filter_by(**key).values(state="RELEASED"))

    def settle(self, attempt_id, tokens, cost, *, currency="TEST", pricing_version="fixture-v1"):
        actual = amount(cost)
        if type(tokens) is not int or not 0 <= tokens <= 2147483647 or not 1 <= len(currency) <= 8 or not 1 <= len(pricing_version) <= 64:
            raise BudgetError("INVALID_USAGE")
        key = self._key(attempt_id)
        # Late real usage must remain accountable even if the original run was cancelled/revoked.
        # This does not authorize another send or any result publication.
        with self.service.engine.begin() as conn:
            conn.execute(select(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"]).with_for_update()).one()
            row = conn.execute(select(attempts).filter_by(**key).with_for_update()).mappings().one()
            if row["state"] == "RELEASED":
                raise BudgetError("ATTEMPT_RELEASED")
            ref = self.service.audit.record_usage(conn, **key, tokens=tokens, cost=actual, currency=currency, pricing_version=pricing_version)
            if row["state"] in ["SETTLED", "SETTLED_OVER_LIMIT"]:
                return ref
            over = actual > row["max_cost"] or tokens > row["max_tokens"]
            conn.execute(update(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"])
                .values(reserved_calls=budgets.c.reserved_calls - 1, reserved_tokens=budgets.c.reserved_tokens - row["max_tokens"],
                        reserved_cost=budgets.c.reserved_cost - row["max_cost"], used_calls=budgets.c.used_calls + 1,
                        used_tokens=budgets.c.used_tokens + tokens, used_cost=budgets.c.used_cost + actual))
            conn.execute(update(attempts).filter_by(**key).values(state="SETTLED_OVER_LIMIT" if over else "SETTLED",
                actual_tokens=tokens, actual_cost=actual, usage_ref=ref))
            self.service.audit.record(conn, tenant_id=key["tenant_id"], principal_id=self.principal.principal_id,
                task_id=key["task_id"], action="USAGE_SETTLED", code="BUDGET_OVERRUN" if over else "OK", details={"usageRef": ref})
            return ref
