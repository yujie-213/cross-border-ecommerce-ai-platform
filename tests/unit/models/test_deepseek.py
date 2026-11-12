from decimal import Decimal
import json
import os
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from commerce_hub.adapters.models.deepseek import DeepSeekProvider, ConnectivityAuthorization
from commerce_hub.adapters.models.mock import sample_output
from commerce_hub.capabilities.models.contracts import ProviderRequest
from commerce_hub.capabilities.models.gateway import ModelGateway
from .support import fixture_bundle, fixture_request, fixture_control


def settings(**changes):
    values = dict(model_network_enabled=False, model_provider="deepseek", model_name="deepseek-flash",
        model_base_url="https://api.deepseek.com", model_max_output_tokens=128,
        model_api_key=SecretStr(os.urandom(24).hex()))
    values.update(changes)
    return SimpleNamespace(**values)


class OfflineConnection:
    """Synthetic official-protocol fixture, NEVER a real DeepSeek success claim."""
    def __init__(self, status=200, **changes):
        self.status = status
        self.closed = False
        self.requests = []
        self.data = dict(id="synthetic-provider-request", model="deepseek-flash",
            choices=[dict(message=dict(content=json.dumps(sample_output())), finish_reason="stop")],
            usage=dict(prompt_tokens=64, completion_tokens=32, total_tokens=96))
        self.data.update(changes)

    def request(self, method, path, *, body, headers):
        self.requests.append((method, path, json.loads(body), headers))

    def getresponse(self):
        return self

    def read(self, size):
        return json.dumps(self.data).encode()[:size]

    def close(self):
        self.closed = True


def execute_offline(connection, config=None, auth=True):
    provider = DeepSeekProvider(config or settings(model_network_enabled=True),
        authorization=ConnectivityAuthorization("offline-fixture", Decimal(".01")) if auth else None,
        connection_factory=lambda *a, **k: connection)
    bundle = fixture_bundle(deployment_id="deepseek-connectivity", model="deepseek-flash", max_output_tokens=128)
    result = ModelGateway(provider).invoke(fixture_request(bundle), fixture_control(), bundle)
    return result, provider


@pytest.mark.parametrize("enabled,authorized", [(False, False), (False, True), (True, False)])
def test_key_configuration_never_authorizes_network(enabled, authorized):
    conn = OfflineConnection()
    result, _ = execute_offline(conn, settings(model_network_enabled=enabled), authorized)
    assert result.code == "NETWORK_DISABLED" and not conn.requests


def test_official_protocol_mapping_and_unknown_billed_cost_are_explicit():
    conn = OfflineConnection()
    config = settings(model_network_enabled=True)
    result, provider = execute_offline(conn, config)
    assert result.code == "OK" and result.validatedObject is not None
    assert result.tokenUsageStatus == "KNOWN" and result.costStatus == "UNKNOWN" and result.usageRef
    assert result.usage.totalTokens == 96 and result.usage.actualCost is None
    assert result.actualModelRevision == "deepseek-flash" and result.usageStatus == "UNKNOWN"
    assert conn.closed and len(conn.requests) == 1
    method, path, body, headers = conn.requests[0]
    assert method == "POST" and path == "/chat/completions"
    assert body["model"] == "deepseek-flash" and body["max_tokens"] == 128
    assert body["thinking"] == {"type": "disabled"} and body["response_format"] == {"type": "json_object"}
    assert "control" not in body and "taskRef" not in json.dumps(body) and "tools" not in body
    assert headers["Authorization"] == "Bearer " + config.model_api_key.get_secret_value()
    assert config.model_api_key.get_secret_value() not in result.model_dump_json()
    assert provider._used


@pytest.mark.parametrize("status,code", [(301,"PROVIDER_ERROR"),(401,"AUTH_ERROR"),(402,"AUTH_ERROR"),
    (429,"RATE_LIMITED"),(500,"UNAVAILABLE")])
def test_http_error_classification_no_redirect_and_no_retries(status,code):
    conn = OfflineConnection(status)
    result,_ = execute_offline(conn)
    assert result.code == code and len(conn.requests) == 1 and conn.closed


@pytest.mark.parametrize("finish,code", [("length","TRUNCATED"),("content_filter","REFUSED"),("tool_calls","PROVIDER_ERROR")])
def test_finish_reason_mapping(finish,code):
    conn = OfflineConnection(choices=[dict(message=dict(content="{}"), finish_reason=finish)])
    result,_=execute_offline(conn)
    assert result.code == code


def test_malformed_json_and_missing_usage_never_fabricate_zero_cost():
    conn = OfflineConnection(usage={})
    result,_=execute_offline(conn)
    assert result.code == "OK" and result.usageRef
    assert result.tokenUsageStatus == "UNKNOWN" and result.usage.totalTokens is None and result.usage.actualCost is None
    conn = OfflineConnection(choices=[dict(message=dict(content="{"), finish_reason="stop")])
    result,_=execute_offline(conn)
    assert result.code == "INVALID_OUTPUT" and result.usageStatus == "UNKNOWN"


def test_transport_timeout_and_sensitive_exception_are_safe():
    for exc,code in [(TimeoutError("Authorization secret"), "TIMEOUT"),(OSError("Authorization secret"), "PROVIDER_ERROR")]:
        conn = OfflineConnection()
        def fail(*a,**k): raise exc
        conn.request=fail
        result,_=execute_offline(conn)
        assert result.code == code and "secret" not in result.model_dump_json() and conn.closed


def test_unknown_usage_fact_has_known_tokens_without_fabricated_charge():
    conn = OfflineConnection()
    provider = DeepSeekProvider(settings(model_network_enabled=True), authorization=ConnectivityAuthorization("offline",Decimal(".01")),
        connection_factory=lambda *a,**k:conn)
    bundle=fixture_bundle(deployment_id="deepseek-connectivity", model="deepseek-flash", max_output_tokens=128)
    request=fixture_request(bundle)
    payload,digests=bundle.resolve(request)
    internal=ProviderRequest(payload=payload,control={**request.model_dump(),"timeoutMs":1000,"digests":digests})
    response=provider.invoke(internal)
    assert response.usage.inputTokens==64 and response.usage.outputTokens==32 and response.usage.actualCost is None
    with pytest.raises(ValueError): provider.invoke(internal)
    assert len(conn.requests)==1


def test_settings_defaults_and_safe_runtime_injection(tmp_path, monkeypatch):
    from commerce_hub.bootstrap.settings import load_settings, ConfigurationError
    for key in list(os.environ):
        if key.startswith(("COMMERCE_", "S01_TEST_")): monkeypatch.delenv(key)
    credential=os.urandom(24).hex()
    path=tmp_path/"fixture.env"
    path.write_text("S01_TEST_DB_HOST=127.0.0.1\nS01_TEST_DB_NAME=s01_a01_test_20261112\nS01_TEST_DB_USER=fixture\nS01_TEST_DB_PASSWORD=fixture\nCOMMERCE_MODEL_API_KEY="+credential)
    config=load_settings(path)
    assert not config.model_network_enabled and config.model_provider=="mock"
    assert config.model_api_key.get_secret_value()==credential and credential not in repr(config)
    monkeypatch.setenv("COMMERCE_MODEL_BASE_URL", "http://untrusted.invalid/path?key="+credential)
    with pytest.raises(ConfigurationError) as error: load_settings(path)
    assert credential not in str(error.value)


def test_connectivity_entry_default_never_reads_settings_or_opens_network(monkeypatch,capsys):
    from tools.deepseek_connectivity import main
    from commerce_hub.bootstrap import settings as module
    monkeypatch.setattr(module,"load_settings",lambda *a,**k:pytest.fail("default probe must not read secrets"))
    assert main([])==0
    assert json.loads(capsys.readouterr().out)["status"]=="NOT_RUN"
    for args in [["--execute"],["--execute","--authorization-id","offline"],
                 ["--execute","--authorization-id","offline","--max-cost-usd","2"]]:
        with pytest.raises(ValueError): main(args)


def test_insufficient_cost_allowance_and_absent_key_are_unsent():
    provider=DeepSeekProvider(settings(model_network_enabled=True),authorization=ConnectivityAuthorization("offline",Decimal(".00001")))
    bundle=fixture_bundle(deployment_id="deepseek-connectivity",model="deepseek-flash",max_output_tokens=128)
    assert ModelGateway(provider).invoke(fixture_request(bundle),fixture_control(),bundle).code=="COST_ALLOWANCE_TOO_SMALL"
    conn=OfflineConnection()
    result,_=execute_offline(conn,settings(model_network_enabled=True,model_api_key=SecretStr("")))
    assert result.code=="CREDENTIAL_MISSING" and not conn.requests
