"""A01 technical control: original O01 allowance, G02 facts, bounded one-shot invocation."""
import hashlib
import threading
import time

from pydantic import ValidationError

from .contracts import ModelRequest, ModelResponse, ProviderRequest, ProviderResult


class ModelGateway:
    def __init__(self, provider, *, timeout_seconds=15, max_concurrent=1):
        if not 0 < timeout_seconds <= 30 or type(max_concurrent) is not int or not 1 <= max_concurrent <= 4:
            raise ValueError("INVALID_GATEWAY_LIMIT")
        self.provider = provider
        self.timeout_seconds, self.max_concurrent = timeout_seconds, max_concurrent
        self.slots = threading.BoundedSemaphore(max_concurrent)

    @staticmethod
    def failure(code, *, usage_status="NOT_SENT", **kwargs):
        return ModelResponse(status="TECH_ERROR", code=code, usageStatus=usage_status, **kwargs)

    def invoke(self, value, context, bundle):
        try:
            # Revalidate even an object supplied via model_construct/model_copy.
            request = ModelRequest.model_validate(value.model_dump() if isinstance(value, ModelRequest) else value)
        except (ValidationError, ValueError, TypeError):
            return self.failure("INVALID_REQUEST")
        budget = context.budget
        admitted = False
        versions = {}
        try:
            if request.queryRef is not None:
                return self.failure("UNSUPPORTED_QUERY")
            context.check()
            binding = budget.validate_model_call(task_ref=request.taskRef.model_dump(),
                principal_ref=request.principalRef.model_dump(), plan_version=request.planVersion,
                policy_ref=request.policyContextRef.model_dump(), attempt_id=request.attemptId,
                logical_call_id=request.logicalCallId, allowance_ref=request.allowanceRef.model_dump(), deadline=request.deadline)
            if binding["state"] != "RESERVED":
                return self.failure("USAGE_MUST_BE_RECONCILED" if binding["state"] in {"SENT", "UNKNOWN"} else "RESULT_UNAVAILABLE",
                    usage_status="UNKNOWN" if binding["state"] in {"SENT", "UNKNOWN"} else "KNOWN")
            admitted = True
            payload, digests = bundle.resolve(request)
            if not set(request.requiredCapabilities) <= self.provider.describe_capabilities():
                raise ValueError("UNSUPPORTED_CAPABILITY")
            # This bound deliberately exceeds UTF-8 bytes plus message framing. Actual usage is still checked.
            token_upper = sum(len(m["content"].encode()) for m in payload["messages"]) + 4096 + payload["parameters"]["maxOutputTokens"]
            if binding["max_tokens"] < token_upper:
                raise ValueError("TOKEN_ALLOWANCE_TOO_SMALL")
            self.provider.preflight(payload, binding["max_cost"])
            versions = {name: getattr(request, name).model_dump() for name in
                ["deploymentRef", "promptRef", "contextBundleRef", "outputSchemaRef", "parametersRef", "cachePolicyRef"]}
            versions.update(digests=digests, configuredModel=payload["modelRevision"])
        except Exception as exc:
            code = self._safe_code(exc, "CONTROL_DENIED")
            if admitted:
                try:
                    budget.release_unsent(request.attemptId)
                except Exception:
                    code = "ACCOUNTING_ERROR"
            return self.failure(code, versionBundle=versions)
        if not self.slots.acquire(blocking=False):
            try:
                budget.release_unsent(request.attemptId)
            except Exception:
                return self.failure("ACCOUNTING_ERROR")
            return self.failure("CONCURRENCY_DENIED")
        start = time.monotonic()
        # DB time anchors the remaining deadline; monotonic time prevents a local wall-clock rollback.
        limit = min(self.timeout_seconds, (request.deadline - binding["now"]).total_seconds())
        details = dict(attemptId=request.attemptId, logicalCallId=request.logicalCallId,
            planVersion=request.planVersion, participantId=request.participantId, snapshotId=request.snapshotId,
            allowanceRef=request.allowanceRef.model_dump(), parentSpanId=request.parentSpanId, versions=versions)
        try:
            context.check()
            binding = budget.validate_model_call(task_ref=request.taskRef.model_dump(),
                principal_ref=request.principalRef.model_dump(), plan_version=request.planVersion,
                policy_ref=request.policyContextRef.model_dump(), attempt_id=request.attemptId,
                logical_call_id=request.logicalCallId, allowance_ref=request.allowanceRef.model_dump(), deadline=request.deadline)
            limit = min(self.timeout_seconds, (request.deadline-binding["now"]).total_seconds())
            elapsed = time.monotonic() - start
            limit -= elapsed
            if limit <= 0:
                raise ValueError("DEADLINE_EXCEEDED")
            provider_request = ProviderRequest(payload=payload, control={**request.model_dump(),
                "timeoutMs": max(1, int(limit * 1000)), "digests": digests})
            budget.send_model(request.attemptId, request.logicalCallId, max_inflight=self.max_concurrent,
                details=details, trace_id=request.traceId)
        except Exception as exc:
            self.slots.release()
            try:
                budget.release_unsent(request.attemptId)
            except Exception:
                pass  # A concurrent send owns this attempt; never release SENT/UNKNOWN.
            return self.failure(self._safe_code(exc, "CONTROL_DENIED"), versionBundle=versions)

        done = threading.Event()
        box = {}

        def invoke_once():
            try:
                # No transaction spans provider IO; no worker branch shares a DB connection.
                context.check()
                if time.monotonic() - start >= limit:
                    raise TimeoutError()
                raw = self.provider.invoke(provider_request)
                result = ProviderResult.model_validate(raw.model_dump() if isinstance(raw, ProviderResult) else raw)
                usage = result.usage
                known = usage.inputTokens is not None and usage.outputTokens is not None and usage.actualCost is not None
                usage_ref = None
                if known:
                    usage_ref = budget.settle(request.attemptId, usage.inputTokens + usage.outputTokens,
                        usage.actualCost, currency=usage.currency, pricing_version=usage.pricingVersion)
                else:
                    budget.unknown(request.attemptId)
                metadata = {**details, "usage": usage.model_dump(mode="json"), "usageStatus": "KNOWN" if known else "UNKNOWN",
                    "usageRef": usage_ref, "actualModelRevision": result.actualModelRevision if result.actualModelRevision == payload["modelRevision"] else None,
                    "reportedModelDigest": hashlib.sha256((result.actualModelRevision or "").encode()).hexdigest(),
                    "providerRequestId": result.providerRequestId, "finishReason": result.finishReason,
                    "elapsedMs": int((time.monotonic() - start) * 1000)}
                audit_ref = budget.model_event(code=result.status, details=metadata, trace_id=request.traceId)
                box.update(result=result, usage_ref=usage_ref, audit_ref=audit_ref, known=known,
                    over=known and (usage.actualCost > binding["max_cost"] or usage.inputTokens+usage.outputTokens > binding["max_tokens"]))
            except Exception:
                try:
                    budget.unknown(request.attemptId)
                    budget.model_event(code="ACCOUNTING_OR_PROVIDER_ERROR", details=details, trace_id=request.traceId)
                except Exception:
                    pass  # SENT already durably occupies the entire reservation.
                box["error"] = "ACCOUNTING_OR_PROVIDER_ERROR"
            finally:
                self.slots.release()  # A timed-out caller cannot free an in-flight provider slot.
                done.set()

        try:
            threading.Thread(target=invoke_once, daemon=True, name="a01-provider").start()
        except Exception:
            self.slots.release()
            budget.unknown(request.attemptId)
            return self.failure("UNAVAILABLE", usage_status="UNKNOWN", versionBundle=versions)
        while True:
            try:
                context.check()
            except Exception as exc:
                return self._stop(budget, request, self._safe_code(exc, "CANCELLED"), details, versions)
            if time.monotonic() - start >= limit:
                return self._stop(budget, request, "TIMEOUT", details, versions)
            if done.wait(min(0.02, max(0.001, limit - (time.monotonic()-start)))):
                break
        # Check again after IO/settlement, including responses arriving at the deadline boundary.
        try:
            context.check()
            if time.monotonic() - start >= limit:
                return self._stop(budget, request, "TIMEOUT", details, versions)
        except Exception as exc:
            return self._stop(budget, request, self._safe_code(exc, "CANCELLED"), details, versions)
        if "error" in box:
            return self.failure(box["error"], usage_status="UNKNOWN", versionBundle=versions)
        result = box["result"]
        common = dict(usageStatus="KNOWN" if box["known"] else "UNKNOWN", usageRef=box["usage_ref"],
            auditRef=box["audit_ref"], finishReason=result.finishReason,
            actualModelRevision=result.actualModelRevision if result.actualModelRevision == payload["modelRevision"] else None,
            versionBundle=versions)
        def outcome(code, validated=None):
            try:
                common["auditRef"] = budget.model_event(code=code, details={**details,
                    "usageRef": common["usageRef"], "providerRequestId": result.providerRequestId,
                    "actualModelRevision": common["actualModelRevision"]}, trace_id=request.traceId)
            except Exception:
                return ModelResponse(status="TECH_ERROR", code="ACCOUNTING_ERROR", **common)
            return ModelResponse(status="SUCCESS" if code == "OK" else "TECH_ERROR", code=code,
                validatedObject=validated if code == "OK" else None, **common)
        if box["over"]:
            return outcome("BUDGET_OVERRUN")
        if result.status != "COMPLETED":
            return outcome(result.status)
        if result.actualModelRevision != payload["modelRevision"]:
            return outcome("MODEL_MISMATCH")
        if result.finishReason != "stop":
            return outcome("TRUNCATED")
        try:
            validated = bundle.validate_output(result.content)
        except (ValidationError, TypeError, ValueError):
            return outcome("INVALID_OUTPUT")
        if not box["known"]:
            return outcome("USAGE_UNKNOWN")
        return outcome("OK", validated)

    @staticmethod
    def _safe_code(exc, default):
        # Exception text may contain HTTP headers, credentials, prompts or SQL. Never return it.
        from commerce_hub.orchestration.budget import BudgetError
        from commerce_hub.orchestration.service import TaskError
        from commerce_hub.governance.access.service import AccessDenied
        from commerce_hub.infrastructure.work import LeaseLost
        if isinstance(exc, TaskError):
            return exc.code
        if isinstance(exc, AccessDenied):
            return "POLICY_DENIED"
        if isinstance(exc, LeaseLost):
            return "LEASE_LOST"
        allowed = {"MODEL_BINDING_DENIED", "DEADLINE_EXCEEDED", "ATTEMPT_NOT_SENDABLE", "USAGE_MUST_BE_RECONCILED",
            "CONCURRENCY_DENIED", "UNSUPPORTED_CAPABILITY", "TOKEN_ALLOWANCE_TOO_SMALL", "UNRESOLVED_REFERENCE",
            "CONTEXT_BINDING_DENIED", "CONTEXT_LIMIT", "NETWORK_DISABLED", "CREDENTIAL_MISSING", "COST_ALLOWANCE_TOO_SMALL",
            "UNSUPPORTED_MODEL"}
        if isinstance(exc, (BudgetError, ValueError)) and len(exc.args) == 1 and exc.args[0] in allowed:
            return exc.args[0]
        return default

    def _stop(self, budget, request, code, details, versions):
        try:
            budget.unknown(request.attemptId)
            ref = budget.model_event(code=code, details=details, trace_id=request.traceId)
        except Exception:
            ref = None
        return self.failure(code, usage_status="UNKNOWN", auditRef=ref, versionBundle=versions)
