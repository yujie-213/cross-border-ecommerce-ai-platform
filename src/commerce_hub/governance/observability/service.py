from uuid import uuid4
from decimal import Decimal
from sqlalchemy import insert, select, update, func
from .tables import audit_events, usage_facts


class Audit:
    def verify_model_receipt(self, connection, *, tenant_id, task_id, receipt):
        """Verify a published response against immutable G02 audit and usage facts."""
        from commerce_hub.capabilities.models.contracts import usage_fingerprint
        event = connection.execute(select(audit_events).filter_by(tenant_id=tenant_id,
            task_id=task_id, event_id=receipt.get("auditRef"))).mappings().first()
        if (event is None or event["action"] != "MODEL_RESULT" or event["code"] != receipt.get("reason")
                or event["details"].get("versions") != receipt.get("versionBundle")
                or event["details"].get("usageDigest") != usage_fingerprint(receipt)):
            raise ValueError("MODEL_RECEIPT_MISMATCH")
        ref = receipt.get("usageRef")
        if ref is not None:
            fact = connection.execute(select(usage_facts).filter_by(tenant_id=tenant_id, task_id=task_id,
                usage_ref=ref)).mappings().first()
            mapping = dict(inputTokens="input_tokens", outputTokens="output_tokens", totalTokens="tokens",
                cachedInputTokens="cached_input_tokens", uncachedInputTokens="uncached_input_tokens",
                actualCost="cost", currency="currency", pricingVersion="pricing_version")
            usage = receipt.get("usage") or {}
            if fact is None:
                raise ValueError("MODEL_RECEIPT_MISMATCH")
            for public, stored in mapping.items():
                value = usage.get(public)
                expected = Decimal(value) if public == "actualCost" and value is not None else value
                if value is not None and fact[stored] != expected:
                    raise ValueError("MODEL_RECEIPT_MISMATCH")

    def usage_dimensions(self, connection, *, tenant_id, task_id, attempt_id):
        row = connection.execute(select(usage_facts).filter_by(tenant_id=tenant_id, task_id=task_id,
            attempt_id=attempt_id)).mappings().one()
        return {name:row[name] for name in ("tokens", "input_tokens", "output_tokens", "cached_input_tokens",
            "uncached_input_tokens", "cost")}

    def record(self, connection, *, tenant_id, principal_id, action, task_id=None, code="OK", trace_id=None, details=None):
        event_id = uuid4().hex
        connection.execute(insert(audit_events).values(tenant_id=tenant_id, event_id=event_id, task_id=task_id,
            principal_id=principal_id, action=action, code=code, occurred_at=func.utc_timestamp(6),
            trace_id=trace_id or uuid4().hex, details=details or {}))
        return event_id

    def record_usage(self, connection, *, tenant_id, task_id, attempt_id, tokens, cost, currency, pricing_version,
                     input_tokens=None, output_tokens=None, cached_input_tokens=None, uncached_input_tokens=None):
        key = dict(tenant_id=tenant_id, task_id=task_id, attempt_id=attempt_id)
        if cost is not None:
            other_currency = connection.execute(select(usage_facts.c.currency).filter_by(tenant_id=tenant_id, task_id=task_id)
                .where(usage_facts.c.attempt_id != attempt_id, usage_facts.c.cost.is_not(None),
                    usage_facts.c.currency != currency).limit(1)).first()
            if other_currency is not None:
                raise ValueError("USAGE_CURRENCY_CONFLICT")
        existing = connection.execute(select(usage_facts).filter_by(**key)).mappings().first()
        values = dict(tokens=tokens, cost=cost, currency=currency, pricing_version=pricing_version,
            input_tokens=input_tokens, output_tokens=output_tokens, cached_input_tokens=cached_input_tokens,
            uncached_input_tokens=uncached_input_tokens)
        if existing:
            # Missing fields never erase facts. Later actual billing may fill an unknown charge.
            if any(existing[name] is not None and value is not None and existing[name] != value for name, value in values.items()):
                raise ValueError("USAGE_CONFLICT")
            merged = {name:existing[name] if existing[name] is not None else value for name,value in values.items()}
            if merged["tokens"] is None and merged["input_tokens"] is not None and merged["output_tokens"] is not None:
                merged["tokens"] = merged["input_tokens"] + merged["output_tokens"]
                if merged["tokens"] > 2147483647:
                    raise ValueError("USAGE_CONFLICT")
            if merged["tokens"] is not None and any(value is not None and value > merged["tokens"]
                    for value in (merged["input_tokens"], merged["output_tokens"])):
                raise ValueError("USAGE_CONFLICT")
            if merged["tokens"] is not None and sum(merged[name] or 0 for name in
                    ("cached_input_tokens", "uncached_input_tokens")) > merged["tokens"]:
                raise ValueError("USAGE_CONFLICT")
            if (merged["input_tokens"] is not None and merged["output_tokens"] is not None
                and merged["tokens"] is not None and merged["tokens"] != merged["input_tokens"] + merged["output_tokens"]):
                raise ValueError("USAGE_CONFLICT")
            if merged["input_tokens"] is not None and any(merged[name] is not None and merged[name] > merged["input_tokens"]
                for name in ("cached_input_tokens", "uncached_input_tokens")):
                raise ValueError("USAGE_CONFLICT")
            if (merged["cached_input_tokens"] is not None and merged["uncached_input_tokens"] is not None
                and merged["input_tokens"] is not None and merged["cached_input_tokens"] + merged["uncached_input_tokens"] != merged["input_tokens"]):
                raise ValueError("USAGE_CONFLICT")
            additions = {name:value for name,value in merged.items() if existing[name] is None and value is not None}
            if additions:
                connection.execute(update(usage_facts).filter_by(**key).values(**additions))
            return existing["usage_ref"]
        ref = uuid4().hex
        connection.execute(insert(usage_facts).values(**key, **values, usage_ref=ref))
        return ref
