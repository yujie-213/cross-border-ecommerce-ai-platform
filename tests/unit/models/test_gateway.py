from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import threading
import time

import pytest
from pydantic import ValidationError

from commerce_hub.adapters.models.mock import MockProvider
from commerce_hub.capabilities.models.contracts import ModelRequest, ProviderRequest, Usage
from commerce_hub.capabilities.models.gateway import ModelGateway
from commerce_hub.orchestration.service import TaskError
from .support import fixture_bundle, fixture_request, fixture_control


@pytest.mark.parametrize("patch", [
    {"parameters": {}}, {"messages": []}, {"deadlineRef": {}}, {"toolSpecs": []}, {"toolSpecsDigest": "f"*64},
    {"schemaVersion": "0.1"}, {"taskRef": {"tenantId": "tenant-fixture", "taskId": "task-fixture", "version": "1"}},
    {"taskRef": None}, {"queryRef": {"tenantId": "tenant-fixture", "queryId": "q"}},
    {"planVersion": None}, {"participantId": None}, {"snapshotId": None},
    {"deadline": "2026-11-12"}, {"deadline": 1}, {"deadline": "2026-11-12T12:00:00+08:00"},
    {"contextBundleRef": {"tenantId": "other", "id": "c", "version": "1"}},
    {"deploymentRef": {"id": "m", "version": "latest"}}, {"toolSpecRefs": [{"id": "write", "version": "1"}]},
    {"requiredCapabilities": ["structured_output", "structured_output"]}, {"attemptId": ""}, {"logicalCallId": 1},
])
def test_invalid_model_request_never_calls_provider(patch):
    req = fixture_request().model_dump(mode="json")
    req.update(patch)
    provider = MockProvider()
    result = ModelGateway(provider).invoke(req, fixture_control(), fixture_bundle())
    assert result.code == "INVALID_REQUEST" and provider.calls == 0


def test_valid_model_request_and_query_shape():
    req = fixture_request().model_dump(mode="json")
    assert ModelRequest.model_validate(req).schemaVersion == "0.2"
    req.update(taskRef=None, queryRef={"tenantId": "tenant-fixture", "queryId": "q"}, planVersion=None, participantId=None)
    assert ModelRequest.model_validate(req).queryRef.queryId == "q"
    assert ModelGateway(MockProvider()).invoke(req, fixture_control(), fixture_bundle()).code == "UNSUPPORTED_QUERY"


@pytest.mark.parametrize("mode,code", [("success", "OK"), ("missing", "INVALID_OUTPUT"), ("type", "INVALID_OUTPUT"),
    ("extra", "INVALID_OUTPUT"), ("json", "INVALID_OUTPUT"), ("refused", "REFUSED"), ("truncated", "TRUNCATED"),
    ("timeout", "TIMEOUT"), ("unavailable", "UNAVAILABLE"), ("rate_limit", "RATE_LIMITED"), ("auth", "AUTH_ERROR"),
    ("model_mismatch", "MODEL_MISMATCH"), pytest.param("unknown", "OK", id="unknown-USAGE_UNKNOWN"), ("exception", "ACCOUNTING_OR_PROVIDER_ERROR")])
def test_schema_and_technical_outcomes(mode, code):
    provider, context = MockProvider(mode=mode), fixture_control()
    result = ModelGateway(provider).invoke(fixture_request(), context, fixture_bundle())
    assert result.code == code and provider.calls == 1
    assert bool(result.validatedObject) == (code == "OK")
    assert result.cacheStatus == "OFF" and result.toolRequests == []
    if mode not in {"unknown", "timeout", "unavailable", "exception"}:
        context.budget.settle.assert_called_once_with("attempt-1", 96, Decimal("0.0001"), currency="TEST", pricing_version="mock-v1",
            input_tokens=64, output_tokens=32, cached_input_tokens=None, uncached_input_tokens=None)
    elif mode == "unknown":
        context.budget.settle.assert_not_called()
        context.budget.record_model_usage.assert_called_once()
        context.budget.unknown.assert_not_called()
        assert result.tokenUsageStatus == result.costStatus == "UNKNOWN"
    else:
        context.budget.settle.assert_not_called()
        context.budget.unknown.assert_called_with("attempt-1")
    assert "SENSITIVE_BODY" not in result.model_dump_json()


def test_provider_request_digests_timeout_and_roles_are_checked():
    provider = MockProvider()
    ModelGateway(provider).invoke(fixture_request(), fixture_control(), fixture_bundle())
    request = provider.requests[0].model_dump()
    assert ProviderRequest.model_validate(request)
    for patch in [lambda r: r["control"].update(timeoutMs=0),
                  lambda r: r["payload"]["messages"][0].update(content="tampered"),
                  lambda r: r["payload"]["parameters"].update(maxOutputTokens=True),
                  lambda r: r["payload"].update(toolSpecs=[{}]),
                  lambda r: r["control"].update(digests={})]:
        copy = deepcopy(request)
        patch(copy)
        with pytest.raises(ValidationError):
            ProviderRequest.model_validate(copy)


@pytest.mark.parametrize("field", ["promptRef", "outputSchemaRef", "parametersRef", "cachePolicyRef"])
def test_unknown_ref_is_unsent_and_released(field):
    request, context, provider = fixture_request().model_dump(), fixture_control(), MockProvider()
    request[field] = {"id": "unregistered", "version": "1"}
    result = ModelGateway(provider).invoke(request, context, fixture_bundle())
    assert result.code == "UNRESOLVED_REFERENCE" and provider.calls == 0
    context.budget.release_unsent.assert_called_once()


def test_cancellation_mid_call_returns_without_waiting_and_late_usage_is_settled():
    entered, release = threading.Event(), threading.Event()
    provider, context = MockProvider(entered=entered, release=release), fixture_control()
    gateway = ModelGateway(provider)
    with ThreadPoolExecutor() as pool:
        future = pool.submit(gateway.invoke, fixture_request(), context, fixture_bundle())
        assert entered.wait(2)
        context.check.side_effect = TaskError("TASK_STOPPED")
        result = future.result(timeout=2)
        assert result.code == "TASK_STOPPED" and result.validatedObject is None
        # Slot belongs to the provider until its IO ends, even after caller cancellation.
        assert not gateway.slots.acquire(blocking=False)
        release.set()
    end = time.monotonic()+2
    while context.budget.settle.call_count == 0 and time.monotonic() < end:
        time.sleep(.01)
    context.budget.settle.assert_called_once()


def test_provider_timeout_is_bounded_and_no_implicit_retry():
    provider, context = MockProvider(delay=.15), fixture_control()
    result = ModelGateway(provider, timeout_seconds=.05).invoke(fixture_request(), context, fixture_bundle())
    assert result.code == "TIMEOUT" and result.usageStatus == "UNKNOWN" and provider.calls == 1
    time.sleep(.2)
    context.budget.settle.assert_called_once()


def test_over_budget_actual_usage_is_accounted_and_output_rejected():
    context = fixture_control()
    context.budget.validate_model_call.side_effect = lambda **kw: dict(state="RESERVED", max_tokens=20000,
        max_cost=Decimal("0"), now=datetime.now(timezone.utc))
    result = ModelGateway(MockProvider()).invoke(fixture_request(), context, fixture_bundle())
    assert result.code == "BUDGET_OVERRUN" and result.validatedObject is None
    context.budget.settle.assert_called_once()


def test_cache_only_token_lower_bound_overrun_rejects_explanation():
    class CacheOnly(MockProvider):
        def invoke(self, request):
            return super().invoke(request).model_copy(update={"usage":Usage(cachedInputTokens=20001)})
    context = fixture_control()
    result = ModelGateway(CacheOnly()).invoke(fixture_request(), context, fixture_bundle())
    assert result.code == "BUDGET_OVERRUN" and result.validatedObject is None
    context.budget.record_model_usage.assert_called_once()


def test_required_usage_audit_failure_never_returns_success():
    context = fixture_control()
    context.budget.model_event.side_effect = RuntimeError("secret Authorization body")
    result = ModelGateway(MockProvider()).invoke(fixture_request(), context, fixture_bundle())
    assert result.code == "ACCOUNTING_OR_PROVIDER_ERROR" and "secret" not in result.model_dump_json()


@pytest.mark.parametrize("stop",["cancel","deadline"])
def test_final_audit_cannot_expose_explanation_after_control_stop(stop):
    context=fixture_control()
    def audit(**event):
        if event["code"]=="OK":
            if stop=="cancel": context.check.side_effect=TaskError("TASK_STOPPED")
            else: time.sleep(.08)
        return "audit-fixture"
    context.budget.model_event.side_effect=audit
    result=ModelGateway(MockProvider(),timeout_seconds=.05 if stop=="deadline" else 5).invoke(
        fixture_request(),context,fixture_bundle())
    assert result.code==("TASK_STOPPED" if stop=="cancel" else "TIMEOUT")
    assert result.validatedObject is None
    context.budget.settle.assert_called_once()


def test_no_sensitive_context_or_output_in_audit(caplog):
    context, provider = fixture_control(), MockProvider()
    bundle = fixture_bundle()
    secret_text = "SENSITIVE SYNTHETIC BODY"
    data = bundle.context.model_dump()
    data["facts"][0]["text"] = secret_text
    bundle = type(bundle)(type(bundle.context).model_validate(data))
    result = ModelGateway(provider).invoke(fixture_request(bundle), context, bundle)
    assert result.code == "OK"
    for call in [*context.budget.send_model.call_args_list, *context.budget.model_event.call_args_list]:
        assert secret_text not in str(call) and "recommendationReasons" not in str(call)
    assert secret_text not in caplog.text


def test_model_cannot_mutate_authoritative_b01_b02_results():
    from tests.support.s01 import snapshot
    from commerce_hub.capabilities.metrics import evaluate
    from commerce_hub.capabilities.forecasting import propose
    snap = snapshot()
    b01, b02 = evaluate(snap), propose(snap)
    original = deepcopy([b01, b02])
    bundle = fixture_bundle()
    data = bundle.context.model_dump()
    data["facts"][0].update(kind="metric", text=json.dumps({"baseline": b01, "candidates": b02}))
    # Use minimal authoritative values instead of transmitting full internal assets.
    data["facts"][0]["text"] = json.dumps({k:b01[k] for k in ["gapQuantity", "firstShortageDate"]})
    bundle = type(bundle)(type(bundle.context).model_validate(data))
    for mode in ["success", "extra"]:
        result = ModelGateway(MockProvider(mode=mode)).invoke(fixture_request(bundle), fixture_control(), bundle)
        assert result.code == ("OK" if mode == "success" else "INVALID_OUTPUT")
        assert [b01,b02] == original
        assert evaluate(snap) == b01 and propose(snap) == b02
