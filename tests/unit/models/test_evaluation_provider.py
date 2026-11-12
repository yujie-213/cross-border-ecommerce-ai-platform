from decimal import Decimal
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr

from commerce_hub.adapters.models.evaluation import (
    EvaluationAuthorization,
    EvaluationProvider,
)
from commerce_hub.capabilities.models.contracts import ProviderRequest
from commerce_hub.capabilities.models.gateway import ModelGateway
from commerce_hub.scenarios.s01.natural_explanation import NaturalExplanationBundle
from tests.unit.models.support import fixture_control, fixture_request
from tests.unit.models.test_natural_explanation import context, output


def settings(**changes):
    values = dict(
        model_network_enabled=True,
        model_provider="deepseek",
        model_name="deepseek-flash",
        model_base_url="https://api.deepseek.com",
        model_max_output_tokens=1024,
        model_api_key=SecretStr(os.urandom(24).hex()),
    )
    values.update(changes)
    return SimpleNamespace(**values)


class OfflineConnection:
    def __init__(self, status=200, **changes):
        self.status = status
        self.closed = False
        self.requests = []
        self.data = dict(
            id="synthetic-evaluation-request",
            model="deepseek-flash",
            choices=[dict(message=dict(content=json.dumps(output(), ensure_ascii=False)), finish_reason="stop")],
            usage=dict(
                prompt_tokens=1000,
                completion_tokens=200,
                total_tokens=1200,
                prompt_cache_hit_tokens=400,
                prompt_cache_miss_tokens=600,
            ),
        )
        self.data.update(changes)

    def request(self, method, path, *, body, headers):
        self.requests.append((method, path, json.loads(body), headers))

    def getresponse(self):
        return self

    def read(self, size):
        return json.dumps(self.data, ensure_ascii=False).encode()[:size]

    def close(self):
        self.closed = True


def assembled(connection, **setting_changes):
    bundle = NaturalExplanationBundle(context())
    provider = EvaluationProvider(
        settings(**setting_changes),
        authorization=EvaluationAuthorization("eval-fixture", 10, Decimal("1")),
        connection_factory=lambda *args, **kwargs: connection,
    )
    return bundle, provider


def direct_request(bundle, logical_call_id="call-1", attempt_id="attempt-1"):
    request = fixture_request(bundle)
    if logical_call_id != "call-1" or attempt_id != "attempt-1":
        value = request.model_dump()
        value.update(logicalCallId=logical_call_id, attemptId=attempt_id,
                     allowanceRef={"tenantId": bundle.context.ref.tenantId, "id": attempt_id, "version": "1"})
        request = type(request).model_validate(value)
    payload, digests = bundle.resolve(request)
    return ProviderRequest(payload=payload, control={**request.model_dump(), "timeoutMs": 1000, "digests": digests})


def test_official_protocol_tokens_are_separate_from_unknown_actual_cost():
    conn = OfflineConnection()
    bundle, provider = assembled(conn)
    result = provider.invoke(direct_request(bundle))
    assert result.status == "COMPLETED" and result.usage.actualCost is None
    assert result.usage.inputTokens == 1000 and result.usage.outputTokens == 200
    exchange = provider.exchange("call-1")
    assert exchange.content and conn.closed and len(conn.requests) == 1
    method, path, body, headers = conn.requests[0]
    assert method == "POST" and path == "/chat/completions"
    assert body["model"] == "deepseek-flash" and body["max_tokens"] == 1024
    assert body["thinking"] == {"type": "disabled"} and body["response_format"] == {"type": "json_object"}
    assert "control" not in body and "tools" not in body
    assert headers["Authorization"].startswith("Bearer ")


def test_gateway_validates_content_with_known_tokens_and_unknown_cost():
    conn = OfflineConnection()
    bundle, provider = assembled(conn)
    control = fixture_control()
    control.budget.record_model_usage.return_value = "usage-fixture"
    result = ModelGateway(provider).invoke(fixture_request(bundle), control, bundle)
    assert result.code == "OK" and result.validatedObject is not None
    assert result.usageStatus == "UNKNOWN"
    assert result.tokenUsageStatus == "KNOWN" and result.costStatus == "UNKNOWN"
    control.budget.record_model_usage.assert_called_once()
    assert bundle.validate_output(provider.exchange("call-1").content)


def test_same_logical_call_is_never_blindly_resent():
    conn = OfflineConnection()
    bundle, provider = assembled(conn)
    request = direct_request(bundle)
    provider.invoke(request)
    with pytest.raises(ValueError, match="USAGE_MUST_BE_RECONCILED"):
        provider.invoke(request)
    assert len(conn.requests) == 1


def test_distinct_logical_calls_use_the_same_bounded_authorization():
    conn = OfflineConnection()
    bundle = NaturalExplanationBundle(context())
    provider = EvaluationProvider(
        settings(),
        authorization=EvaluationAuthorization("eval-two", 2, Decimal("1"), Decimal("0.5")),
        connection_factory=lambda *args, **kwargs: conn,
    )
    assert provider.invoke(direct_request(bundle, "call-a", "attempt-a")).status == "COMPLETED"
    assert provider.invoke(direct_request(bundle, "call-b", "attempt-b")).status == "COMPLETED"
    with pytest.raises(ValueError, match="BUDGET_DENIED"):
        provider.invoke(direct_request(bundle, "call-c", "attempt-c"))
    assert len(conn.requests) == 2


@pytest.mark.parametrize("status,expected", [
    (301, "PROVIDER_ERROR"), (401, "AUTH_ERROR"), (429, "RATE_LIMITED"), (503, "UNAVAILABLE"),
])
def test_http_failures_do_not_redirect_or_retry(status, expected):
    conn = OfflineConnection(status=status)
    bundle, provider = assembled(conn)
    assert provider.invoke(direct_request(bundle)).status == expected
    assert len(conn.requests) == 1 and conn.closed


@pytest.mark.parametrize("changes,code", [
    ({"model_network_enabled": False}, "NETWORK_DISABLED"),
    ({"model_name": "deepseek-chat"}, "UNSUPPORTED_MODEL"),
    ({"model_base_url": "https://example.invalid"}, "UNSUPPORTED_MODEL"),
    ({"model_api_key": SecretStr("")}, "CREDENTIAL_MISSING"),
])
def test_preflight_is_fail_closed(changes, code):
    conn = OfflineConnection()
    bundle, provider = assembled(conn, **changes)
    with pytest.raises(ValueError, match=code):
        provider.preflight(bundle.resolve_content()[0], Decimal("1"))
    assert not conn.requests


def test_malformed_usage_is_unknown_and_never_zero_cost():
    conn = OfflineConnection(usage={})
    bundle, provider = assembled(conn)
    result = provider.invoke(direct_request(bundle))
    assert result.usage.actualCost is None and result.usage.inputTokens is None


def test_partial_usage_preserves_each_known_dimension():
    conn = OfflineConnection(usage={"prompt_tokens": 1000})
    bundle, provider = assembled(conn)
    result = provider.invoke(direct_request(bundle))
    assert result.usage.inputTokens == 1000
    assert result.usage.outputTokens is None and result.usage.totalTokens is None


def test_evaluation_tool_is_default_off_and_offline_suite_covers_a_to_e(monkeypatch, capsys):
    from commerce_hub.bootstrap import settings as settings_module
    from tools.s01_model_evaluation import main
    monkeypatch.setattr(settings_module, "load_settings", lambda *args, **kwargs: pytest.fail("offline mode read settings"))
    assert main([]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "NOT_RUN"
    assert main(["--offline-suite"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report == {"status": "PASS", "accepted": 5, "rejected": 3, "network": "NOT_USED", "c04": "NOT_RUN"}


@pytest.mark.parametrize("args", [
    ["--execute"],
    ["--execute", "--authorization-id", "other", "--max-cost-usd", "1", "--request-risk-usd", "0.05",
     "--max-requests", "5", "--private-output", "data/private/result.json"],
])
def test_evaluation_tool_rejects_missing_or_nonfixed_authorization_before_settings(monkeypatch, args):
    from commerce_hub.bootstrap import settings as settings_module
    from tools.s01_model_evaluation import main
    monkeypatch.setattr(settings_module, "load_settings", lambda *a, **k: pytest.fail("invalid invocation read settings"))
    with pytest.raises(ValueError):
        main(args)


def test_private_teaching_catalog_is_bound_to_authorization_tenant_scope_and_case_sequence():
    from tools.s01_model_evaluation import CATALOG_SCHEMA_VERSION, _load_private_catalog
    from tests.support.admission import build_teaching_admission_package

    private_root = Path("data/private") / ("test-model-catalog-" + uuid4().hex)
    private_root.mkdir(parents=True)
    payload = build_teaching_admission_package()
    tenant = payload["scope"]["tenantId"]
    catalog = dict(
        schemaVersion=CATALOG_SCHEMA_VERSION,
        authorizationId="fixed-auth",
        tenantId=tenant,
        entries=[dict(caseId="A", kind="TEACHING_SIMULATION", payload=payload)],
    )
    path = private_root / "catalog.json"
    try:
        path.write_text(json.dumps(catalog), encoding="utf-8")
        case_ids, entries, scope = _load_private_catalog(
            path, private_root=private_root, authorization_id="fixed-auth", tenant=tenant,
        )
        assert case_ids == ["A"] and entries[0]["kind"] == "TEACHING_SIMULATION"
        assert scope == payload["scope"]

        catalog["authorizationId"] = "other-auth"
        path.write_text(json.dumps(catalog), encoding="utf-8")
        with pytest.raises(ValueError, match="PRIVATE_CATALOG_BINDING_REJECTED"):
            _load_private_catalog(path, private_root=private_root,
                                  authorization_id="fixed-auth", tenant=tenant)
    finally:
        path.unlink(missing_ok=True)
        private_root.rmdir()


def test_private_catalog_path_cannot_escape_private_root():
    from tools.s01_model_evaluation import _load_private_catalog

    private_root = Path("data/private") / ("test-model-root-" + uuid4().hex)
    private_root.mkdir(parents=True)
    outside = Path("data/private") / ("test-model-outside-" + uuid4().hex + ".json")
    try:
        outside.write_text("{}", encoding="utf-8")
        with pytest.raises(ValueError, match="CONTROLLED_PRIVATE_CATALOG_REQUIRED"):
            _load_private_catalog(outside, private_root=private_root,
                                  authorization_id="fixed-auth", tenant="fixed-tenant")
    finally:
        outside.unlink(missing_ok=True)
        private_root.rmdir()


def test_evaluation_cli_client_creates_once_then_only_polls_and_reads_report(monkeypatch):
    from tools.s01_model_evaluation import _create_and_wait

    class Response:
        def __init__(self, status, value):
            self.status_code, self.value = status, value

        def json(self):
            return self.value

    class Client:
        def __init__(self):
            self.posts, self.gets = [], []
            self.states = [
                {"state": "RUNNING", "taskRef": {"tenantId": "tenant", "taskId": "task"}},
                {"state": "SUCCEEDED", "taskRef": {"tenantId": "tenant", "taskId": "task"}},
            ]

        def post(self, path, **kwargs):
            self.posts.append((path, kwargs))
            return Response(202, {"state": "QUEUED", "taskRef": {"tenantId": "tenant", "taskId": "task"}})

        def get(self, path):
            self.gets.append(path)
            if path.endswith("/report"):
                return Response(200, {"reportRef": {"tenantId": "tenant", "reportId": "report"}})
            return Response(200, self.states.pop(0))

    monkeypatch.setattr("tools.s01_model_evaluation.time.sleep", lambda _: None)
    client = Client()
    created, current, report = _create_and_wait(
        client, body={"scenarioId": "S01_MODEL_EVALUATION"}, command_key="fixed-key",
        wait_seconds=10, poll_seconds=0,
    )
    assert created["taskRef"] == current["taskRef"]
    assert current["state"] == "SUCCEEDED" and report["reportRef"]["reportId"] == "report"
    assert len(client.posts) == 1
    assert client.posts[0][1]["headers"] == {"Idempotency-Key": "fixed-key"}
    assert client.gets == [
        "/api/v1/analysis-tasks/task", "/api/v1/analysis-tasks/task",
        "/api/v1/analysis-tasks/task/report",
    ]


def test_managed_process_environment_forces_single_delivery_and_fixed_deadline():
    from tools.s01_model_evaluation import _process_environment

    repository = Path.cwd()
    environment = _process_environment(
        repository=repository, catalog_path=None, evaluation_ref="s01-eval-fixture",
        private_output=repository / "data/private/fixture.json",
    )
    assert environment["COMMERCE_S01_MODEL_EVALUATION_ENABLED"] == "true"
    assert environment["COMMERCE_MAX_DELIVERY_ATTEMPTS"] == "1"
    assert environment["COMMERCE_TASK_DEADLINE_SECONDS"] == "600"
    assert environment["COMMERCE_S01_MODEL_EVALUATION_REF"] == "s01-eval-fixture"
    assert "COMMERCE_S01_MODEL_EVALUATION_CATALOG_PATH" not in environment


def test_fixed_identity_token_covers_full_bounded_poll_window():
    import jwt
    from tools.s01_model_evaluation import IDENTITY_TTL_MINUTES, _identity_expiration, _issue_token

    now = datetime(2026, 11, 12, tzinfo=timezone.utc)
    expires_at = _identity_expiration(now)
    configured = settings()
    configured.auth_issuer = "s01-model-evaluation"
    configured.auth_audience = "s01-model-evaluation"
    configured.auth_signing_key = SecretStr("k" * 48)
    token = _issue_token(
        configured, tenant="tenant", principal_id="principal", identity="identity",
        revision=1, now=now, expires_at=expires_at,
    )
    claims = jwt.decode(
        token, configured.auth_signing_key.get_secret_value(), algorithms=["HS256"],
        issuer=configured.auth_issuer, audience=configured.auth_audience,
        options={"verify_exp": False},
    )
    assert IDENTITY_TTL_MINUTES == 16
    assert claims["exp"] - claims["iat"] == 960
    assert claims["exp"] - claims["iat"] > 900
