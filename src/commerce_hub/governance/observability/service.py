from uuid import uuid4
from sqlalchemy import insert, select, func
from .tables import audit_events, usage_facts


class Audit:
    def record(self, connection, *, tenant_id, principal_id, action, task_id=None, code="OK", trace_id=None, details=None):
        event_id = uuid4().hex
        connection.execute(insert(audit_events).values(tenant_id=tenant_id, event_id=event_id, task_id=task_id,
            principal_id=principal_id, action=action, code=code, occurred_at=func.utc_timestamp(6),
            trace_id=trace_id or uuid4().hex, details=details or {}))
        return event_id

    def record_usage(self, connection, *, tenant_id, task_id, attempt_id, tokens, cost, currency, pricing_version):
        key = dict(tenant_id=tenant_id, task_id=task_id, attempt_id=attempt_id)
        existing = connection.execute(select(usage_facts).filter_by(**key)).mappings().first()
        if existing:
            if (existing["tokens"], existing["cost"], existing["currency"], existing["pricing_version"]) != (tokens, cost, currency, pricing_version):
                raise ValueError("USAGE_CONFLICT")
            return existing["usage_ref"]
        ref = uuid4().hex
        connection.execute(insert(usage_facts).values(**key, tokens=tokens, cost=cost,
                            currency=currency, pricing_version=pricing_version, usage_ref=ref))
        return ref
