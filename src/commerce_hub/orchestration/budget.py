"""O01 original-task allowance control. G02 owns actual usage facts."""
from decimal import Decimal, InvalidOperation
from datetime import timezone
from contextlib import contextmanager
import hashlib

from sqlalchemy import insert, select, update, func

from .tables import budgets, attempts, tasks


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

    @property
    def shared_authorization(self):
        spec=next((s for s in self.service.registry.values() if s.work_kind == self.lease.kind),None)
        return spec.shared_model_authorization if spec else None

    @contextmanager
    def admission_transaction(self):
        """Serialize a bounded authorization across processes; no lock spans IO.

        All facts/reservations stay in existing O01/G02 rows. The named lock is
        released only after commit, and is connection-scoped on crash.
        """
        shared=self.shared_authorization
        if shared is None:
            with self.service.engine.begin() as conn:yield conn
            return
        name='o01:model-auth:'+hashlib.sha256(shared.authorization_id.encode()).hexdigest()[:40]
        with self.service.engine.connect() as conn:
            held=conn.scalar(select(func.get_lock(name,5)))
            conn.commit()
            if held != 1:raise BudgetError('CONCURRENCY_DENIED')
            try:
                with conn.begin():yield conn
            finally:
                if conn.in_transaction():conn.rollback()
                conn.execute(select(func.release_lock(name)))
                conn.commit()

    def check_shared_reservation(self,conn,tokens,cost):
        shared=self.shared_authorization
        if shared is None:return
        totals=conn.execute(select(func.coalesce(func.sum(budgets.c.used_calls+budgets.c.reserved_calls),0),
            func.coalesce(func.sum(budgets.c.used_tokens+budgets.c.reserved_tokens),0),
            func.coalesce(func.sum(budgets.c.used_cost+budgets.c.reserved_cost),0))
            .where(budgets.c.policy_version==shared.authorization_id)).one()
        if totals[0]+1>shared.max_calls or totals[1]+tokens>shared.max_tokens or totals[2]+cost>shared.max_cost:
            raise BudgetError('BUDGET_DENIED')

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
        with self.admission_transaction() as conn:
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
            shared=self.shared_authorization
            if shared is not None:
                active=conn.execute(select(attempts.c.state).select_from(attempts.join(budgets,
                    (attempts.c.tenant_id==budgets.c.tenant_id)&(attempts.c.task_id==budgets.c.task_id)))
                    .where(budgets.c.policy_version==shared.authorization_id,attempts.c.state.in_(['SENT','UNKNOWN']))).scalars().all()
                if active:raise BudgetError('USAGE_MUST_BE_RECONCILED' if 'UNKNOWN' in active else 'CONCURRENCY_DENIED')
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
        with self.admission_transaction() as conn:
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
                .where(attempts.c.state.in_(["SENT", "UNKNOWN", "USAGE_RECORDED", "USAGE_OVER_LIMIT"]))).first()
            if unresolved:
                raise BudgetError("USAGE_MUST_BE_RECONCILED")
            self.check_shared_reservation(conn,tokens,upper)
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

    def settle(self, attempt_id, tokens, cost, *, currency="TEST", pricing_version="fixture-v1",
               input_tokens=None, output_tokens=None, cached_input_tokens=None, uncached_input_tokens=None):
        """Legacy complete settlement; optional token dimensions are additive."""
        return self.record_model_usage(attempt_id, total_tokens=tokens, cost=amount(cost), currency=currency,
            pricing_version=pricing_version, input_tokens=input_tokens, output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens, uncached_input_tokens=uncached_input_tokens)

    def record_model_usage(self, attempt_id, *, total_tokens=None, input_tokens=None, output_tokens=None,
                           cached_input_tokens=None, uncached_input_tokens=None, cost=None,
                           currency=None, pricing_version=None):
        """Record provider-neutral facts; an unknown dimension retains its reservation.

        The existing G02 row is the sole fact. Null may be enriched by a later
        authoritative fact, but a known value can never be replaced or refunded.
        """
        actual = None if cost is None else amount(cost)
        counts = (total_tokens, input_tokens, output_tokens, cached_input_tokens, uncached_input_tokens)
        if (any(value is not None and (type(value) is not int or not 0 <= value <= 2147483647) for value in counts)
            or currency is not None and (not isinstance(currency, str) or not 1 <= len(currency) <= 8)
            or pricing_version is not None and (not isinstance(pricing_version, str) or not 1 <= len(pricing_version) <= 64)
            or actual is not None and currency is None):
            raise BudgetError("INVALID_USAGE")
        if input_tokens is not None and output_tokens is not None:
            if total_tokens is None:
                total_tokens = input_tokens + output_tokens
            if total_tokens != input_tokens + output_tokens or total_tokens > 2147483647:
                raise BudgetError("INVALID_USAGE")
        if input_tokens is not None and (any(value is not None and value > input_tokens for value in (cached_input_tokens, uncached_input_tokens))
            or cached_input_tokens is not None and uncached_input_tokens is not None and cached_input_tokens + uncached_input_tokens != input_tokens):
            raise BudgetError("INVALID_USAGE")
        if total_tokens is not None and (any(value is not None and value > total_tokens for value in (input_tokens, output_tokens))
                or sum(value or 0 for value in (cached_input_tokens, uncached_input_tokens)) > total_tokens):
            raise BudgetError("INVALID_USAGE")
        key = self._key(attempt_id)
        # Late real usage must remain accountable even if the original run was cancelled/revoked.
        # This does not authorize another send or any result publication.
        with self.service.engine.begin() as conn:
            conn.execute(select(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"]).with_for_update()).one()
            row = conn.execute(select(attempts).filter_by(**key).with_for_update()).mappings().one()
            task = conn.execute(select(tasks.c.scenario_id).filter_by(
                tenant_id=key["tenant_id"], task_id=key["task_id"])).mappings().one()
            spec = self.service.registry.get(task["scenario_id"])
            policy_currency = spec.cost_currency if spec else None
            if actual is not None and policy_currency is not None and currency != policy_currency:
                raise BudgetError("USAGE_CURRENCY_CONFLICT")
            if row["state"] == "RELEASED":
                raise BudgetError("ATTEMPT_RELEASED")
            if row["state"] not in ["SENT", "UNKNOWN", "SETTLED", "SETTLED_OVER_LIMIT", "USAGE_RECORDED", "USAGE_OVER_LIMIT"]:
                raise BudgetError("ATTEMPT_NOT_SETTLEABLE")
            ref = self.service.audit.record_usage(conn, **key, tokens=total_tokens, cost=actual, currency=currency,
                pricing_version=pricing_version, input_tokens=input_tokens, output_tokens=output_tokens,
                cached_input_tokens=cached_input_tokens, uncached_input_tokens=uncached_input_tokens)
            effective = self.service.audit.usage_dimensions(conn, **key)
            total_tokens, actual = effective["tokens"], effective["cost"]
            first = row["state"] in {"SENT", "UNKNOWN"}
            token_new = row["actual_tokens"] is None and total_tokens is not None
            cost_new = row["actual_cost"] is None and actual is not None
            updates = {}
            if first:
                updates.update(reserved_calls=budgets.c.reserved_calls - 1, used_calls=budgets.c.used_calls + 1)
            if token_new:
                updates.update(reserved_tokens=budgets.c.reserved_tokens - row["max_tokens"], used_tokens=budgets.c.used_tokens + total_tokens)
            if cost_new:
                updates.update(reserved_cost=budgets.c.reserved_cost - row["max_cost"], used_cost=budgets.c.used_cost + actual)
            effective_tokens = total_tokens if token_new else row["actual_tokens"]
            effective_cost = actual if cost_new else row["actual_cost"]
            over = (row["state"] in {"SETTLED_OVER_LIMIT", "USAGE_OVER_LIMIT"}
                    or effective_tokens is not None and effective_tokens > row["max_tokens"]
                    or any(effective[name] is not None and effective[name] > row["max_tokens"] for name in ("input_tokens", "output_tokens"))
                    or sum(effective[name] or 0 for name in ("cached_input_tokens", "uncached_input_tokens")) > row["max_tokens"]
                    or effective_cost is not None and effective_cost > row["max_cost"])
            complete = effective_tokens is not None and effective_cost is not None
            state = ("SETTLED_OVER_LIMIT" if over else "SETTLED") if complete else ("USAGE_OVER_LIMIT" if over else "USAGE_RECORDED")
            if updates:
                conn.execute(update(budgets).filter_by(tenant_id=key["tenant_id"], task_id=key["task_id"]).values(**updates))
            conn.execute(update(attempts).filter_by(**key).values(state=state,
                actual_tokens=effective_tokens, actual_cost=effective_cost, usage_ref=ref))
            if first or token_new or cost_new:
                self.service.audit.record(conn, tenant_id=key["tenant_id"], principal_id=self.principal.principal_id,
                    task_id=key["task_id"], action="USAGE_SETTLED" if complete else "USAGE_RECORDED",
                    code="BUDGET_OVERRUN" if over else "OK", details={"usageRef": ref,
                        "tokenUsageStatus": "KNOWN" if effective_tokens is not None else "UNKNOWN",
                        "costStatus": "KNOWN" if effective_cost is not None else "UNKNOWN"})
            return ref
