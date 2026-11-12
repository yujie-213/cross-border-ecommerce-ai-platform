import io
import json
import logging
import re

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
import pytest

from commerce_hub.bootstrap.logging import SafeJsonFormatter, trace_id
from commerce_hub.bootstrap.settings import ConfigurationError, Settings, load_settings
from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.entrypoints.http.errors import ApiError


FIXTURE_SECRET = "fixture-only-do-not-log-credential"


@pytest.fixture(autouse=True)
def isolate_runtime(monkeypatch):
    for field in Settings.model_fields.values():
        monkeypatch.delenv(field.validation_alias, raising=False)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeJsonFormatter())
    logger = logging.getLogger("commerce_hub")
    monkeypatch.setattr(logger, "handlers", [handler])
    monkeypatch.setattr(logger, "propagate", False)
    yield stream


@pytest.fixture
def settings():
    return Settings(S01_TEST_DB_HOST="127.0.0.1", S01_TEST_DB_NAME="s01_a01_test_20261112",
                    S01_TEST_DB_USER="fixture-user", S01_TEST_DB_PASSWORD=FIXTURE_SECRET,
                    COMMERCE_ENVIRONMENT="test")


def test_missing_required_settings_fail_safely():
    with pytest.raises(ConfigurationError) as error:
        load_settings(env_file=None)
    assert "S01_TEST_DB_PASSWORD" in str(error.value)
    assert "input_value" not in str(error.value)


def test_invalid_settings_never_echo_secret(tmp_path):
    config = tmp_path / "settings.env"
    config.write_text(f'S01_TEST_DB_HOST=127.0.0.1\nS01_TEST_DB_NAME=x\nS01_TEST_DB_USER=u\n'
                      f'S01_TEST_DB_PASSWORD="{FIXTURE_SECRET}"\nS01_TEST_DB_PORT={FIXTURE_SECRET}\n', encoding="utf-8")
    with pytest.raises(ConfigurationError) as error:
        load_settings(config)
    assert FIXTURE_SECRET not in str(error.value)
    assert "S01_TEST_DB_PORT" in str(error.value)


def test_literal_dotenv_secrets_and_environment_precedence(tmp_path, monkeypatch):
    config = tmp_path / "settings.env"
    password = "${NOT_EXPANDED}#literal"
    config.write_text('S01_TEST_DB_HOST=127.0.0.1\nS01_TEST_DB_NAME=test_db\nS01_TEST_DB_USER=fixture\n'
                      f'S01_TEST_DB_PASSWORD="{password}"\n', encoding="utf-8")
    assert load_settings(config).db_password.get_secret_value() == password
    monkeypatch.setenv("S01_TEST_DB_PASSWORD", FIXTURE_SECRET)
    loaded = load_settings(config)
    assert loaded.db_password.get_secret_value() == FIXTURE_SECRET
    assert FIXTURE_SECRET not in repr(loaded)
    assert "fixture" not in repr(loaded)


def test_remote_database_without_trusted_ca_fails(tmp_path):
    config = tmp_path / "settings.env"
    config.write_text(f'S01_TEST_DB_HOST=db.example.invalid\nS01_TEST_DB_NAME=test_db\n'
                      f'S01_TEST_DB_USER=fixture\nS01_TEST_DB_PASSWORD="{FIXTURE_SECRET}"\n', encoding="utf-8")
    with pytest.raises(ConfigurationError) as error:
        load_settings(config)
    assert FIXTURE_SECRET not in str(error.value)


def test_startup_does_not_connect_or_launch_background_work(settings, monkeypatch):
    calls = []
    def forbidden_connect(**_):
        calls.append("connect")
        raise RuntimeError("unexpected startup connection")
    monkeypatch.setattr("commerce_hub.bootstrap.database.pymysql.connect", forbidden_connect)
    with TestClient(create_app(settings)) as client:
        assert client.get("/health/live").json() == {"status": "alive"}
    assert calls == []


@pytest.mark.parametrize("connected", [True, False])
def test_readiness_does_not_claim_unimplemented_capabilities(settings, connected, monkeypatch):
    app = create_app(settings)
    with TestClient(app) as client:
        monkeypatch.setattr(app.state.database, "check", lambda: connected)
        response = client.get("/health/ready")
        assert response.status_code == 503
        body = response.json()
        assert set(body) == {"code", "message", "details", "traceId", "retryable"}
        assert body["code"] == "NOT_READY"
        assert body["details"]["database"] == ("available" if connected else "unavailable")
        assert body["details"]["s01"] == "not_implemented"
        assert body["retryable"] is (not connected)
        assert response.headers["X-Trace-Id"] == body["traceId"]


def test_database_failure_is_sanitized(settings, monkeypatch, isolate_runtime):
    def failed(**_):
        raise RuntimeError(FIXTURE_SECRET)
    monkeypatch.setattr("commerce_hub.bootstrap.database.pymysql.connect", failed)
    with TestClient(create_app(settings)) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert FIXTURE_SECRET not in response.text
    assert FIXTURE_SECRET not in isolate_runtime.getvalue()
    assert "database_unavailable" in isolate_runtime.getvalue()


def test_trace_headers_and_no_request_data_in_logs(settings, isolate_runtime):
    with TestClient(create_app(settings)) as client:
        trusted_shape = "a" * 32
        response = client.get("/health/live", headers={"X-Trace-Id": trusted_shape})
        assert response.headers["X-Trace-Id"] == trusted_shape
        invalid = client.get("/" + FIXTURE_SECRET, params={"password": FIXTURE_SECRET},
                             headers={"X-Trace-Id": FIXTURE_SECRET, "Authorization": FIXTURE_SECRET})
        assert invalid.status_code == 404
        assert re.fullmatch(r"[a-f0-9]{32}", invalid.headers["X-Trace-Id"])
        assert invalid.headers["Cache-Control"] == "no-store"
        assert FIXTURE_SECRET not in invalid.text
    assert FIXTURE_SECRET not in isolate_runtime.getvalue()
    assert trace_id.get() is None


@pytest.mark.parametrize("status,code", [(401, "UNAUTHENTICATED"), (403, "POLICY_DENIED"),
                                        (404, "NOT_FOUND"), (409, "CONFLICT")])
def test_http_error_contract_drops_unsafe_details(settings, status, code):
    app = create_app(settings)
    @app.get("/_test/http")
    def failure():
        raise HTTPException(status_code=status, detail=FIXTURE_SECRET)
    with TestClient(app) as client:
        response = client.get("/_test/http")
        assert response.status_code == status
        assert response.json()["code"] == code
        assert FIXTURE_SECRET not in response.text


def test_validation_and_unhandled_error_are_safe(settings, isolate_runtime):
    app = create_app(settings)
    class Payload(BaseModel):
        amount: int
    @app.post("/_test/validate")
    def validate(payload: Payload):
        return payload
    @app.get("/_test/crash")
    def crash():
        raise RuntimeError(FIXTURE_SECRET)
    @app.get("/_test/domain")
    def domain():
        raise ApiError("CONFLICT", 409, "State conflict")
    with TestClient(app) as client:
        invalid = client.post("/_test/validate", json={"amount": FIXTURE_SECRET})
        assert invalid.status_code == 422
        assert invalid.json()["code"] == "INVALID_REQUEST"
        assert FIXTURE_SECRET not in invalid.text
        failed = client.get("/_test/crash")
        assert failed.status_code == 500
        assert failed.json()["code"] == "INTERNAL_ERROR"
        assert FIXTURE_SECRET not in failed.text
        assert client.get("/_test/domain").status_code == 409
    assert FIXTURE_SECRET not in isolate_runtime.getvalue()


def test_logger_discards_arbitrary_message_arguments_and_traceback(isolate_runtime):
    logger = logging.getLogger("commerce_hub")
    try:
        raise RuntimeError(FIXTURE_SECRET)
    except RuntimeError:
        logger.error("unsafe %s", FIXTURE_SECRET, exc_info=True, extra={"event": FIXTURE_SECRET})
    logged = isolate_runtime.getvalue()
    assert FIXTURE_SECRET not in logged
    assert json.loads(logged)["event"] == "redacted_event"


@pytest.mark.parametrize("path", ["/api/v1/analysis-tasks", "/api/v1/reports", "/api/v1/executions",
                                  "/api/v1/approvals", "/api/v1/models", "/docs", "/openapi.json"])
def test_unimplemented_routes_are_not_registered(settings, path):
    app = create_app(settings)
    assert {route.path for route in app.routes} == {"/health/live", "/health/ready"}
    with TestClient(app) as client:
        assert client.get(path).status_code == 404
