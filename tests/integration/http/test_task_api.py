from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
import jwt
from pydantic import SecretStr
import pytest

from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.governance.access import AccessControl
from commerce_hub.orchestration.service import HandlerSpec
from tests.support.foundation import EngineeringHandler

pytestmark = pytest.mark.mysql


@pytest.fixture
def http_fixture(database, mysql_settings):
    key = "fixture-http-signing-key-" + "z" * 64
    settings = mysql_settings.model_copy(update={"environment": "test", "auth_issuer": "fixture-http-issuer",
        "auth_audience": "fixture-http-audience", "auth_signing_key": SecretStr(key), "browser_origin": "https://testserver"})
    scope = {"tenantId": "http-" + uuid4().hex, "storeIds": ["store-fixture"], "warehouseIds": ["wh-fixture"],
             "canonicalSkuIds": ["sku-fixture"], "fields": ["status"]}
    access = AccessControl(database.engine, settings.auth_issuer, settings.auth_audience, key)
    now = datetime.now(timezone.utc)
    token_id = uuid4().hex
    with database.engine.begin() as conn:
        access.provision_fixture(conn, tenant_id=scope["tenantId"], principal_id="actor-fixture", token_id=token_id,
            expires_at=now + timedelta(minutes=10), grants_by_action={a: scope for a in
                ["tasks:create", "tasks:read", "tasks:cancel", "engineering:execute"]})
    claims = dict(sub="actor-fixture", tid=scope["tenantId"], jti=token_id, rev=1, iat=int(now.timestamp()),
                  nbf=int(now.timestamp()), exp=int((now + timedelta(minutes=10)).timestamp()),
                  iss=settings.auth_issuer, aud=settings.auth_audience)
    token = jwt.encode(claims, key, algorithm="HS256")
    spec = HandlerSpec("ENGINEERING_FIXTURE", "1", "o01.http." + uuid4().hex, EngineeringHandler())
    return settings, {spec.scenario_id: spec}, token, scope, claims, key


def request_body(scope):
    return {"analysisMode": "SINGLE", "scenarioId": "ENGINEERING_FIXTURE",
            "scope": {k: v for k, v in scope.items() if k != "tenantId"}, "parameters": {}}


def test_authenticated_accept_query_and_idempotency(http_fixture):
    settings, registry, token, scope, _, _ = http_fixture
    with TestClient(create_app(settings, registry)) as client:
        headers = {"Authorization": "Bearer " + token, "Idempotency-Key": uuid4().hex}
        response = client.post("/api/v1/analysis-tasks", json=request_body(scope), headers=headers)
        assert response.status_code == 202
        view = response.json()
        assert response.headers["Location"].endswith(view["taskRef"]["taskId"])
        assert view["reportRef"] is None and view["sourceNature"] == "SIMULATED_ENGINEERING"
        assert client.post("/api/v1/analysis-tasks", json=request_body(scope), headers=headers).json() == view
        assert client.get(response.headers["Location"], headers=headers).json() == view
        assert client.get("/health/ready").json()["scope"] == "ENGINEERING_FOUNDATION_ONLY"
        assert token not in response.text


def test_cookie_csrf_origin_revocation_and_safe_cookie_flags(http_fixture):
    settings, registry, token, scope, _, _ = http_fixture
    with TestClient(create_app(settings, registry), base_url="https://testserver") as client:
        response = client.post("/api/v1/session", headers={"Authorization": "Bearer " + token})
        assert response.status_code == 200 and token not in response.text
        session_cookie = [h for h in response.headers.get_list("set-cookie") if h.startswith("commerce_session=")][0]
        assert "HttpOnly" in session_cookie and "Secure" in session_cookie and "SameSite=strict" in session_cookie
        body = request_body(scope)
        command = {"Idempotency-Key": uuid4().hex}
        assert client.post("/api/v1/analysis-tasks", json=body, headers=command).status_code == 403
        csrf = client.cookies.get("commerce_csrf")
        headers = dict(command, **{"X-CSRF-Token": csrf, "Origin": "https://evil.invalid"})
        assert client.post("/api/v1/analysis-tasks", json=body, headers=headers).status_code == 403
        headers["Origin"] = "https://testserver"
        response = client.post("/api/v1/analysis-tasks", json=body, headers=headers)
        assert response.status_code == 202
        assert client.get(response.headers["Location"]).status_code == 200
        assert client.delete("/api/v1/session").status_code == 403
        assert client.delete("/api/v1/session", headers=headers).status_code == 200
        assert client.get(response.headers["Location"], headers={"Authorization": "Bearer " + token}).status_code == 403


@pytest.mark.parametrize("alteration", ["signature", "issuer", "audience", "expired"])
def test_bad_identity_fails_before_command(http_fixture, alteration):
    settings, registry, token, scope, claims, key = http_fixture
    claims = dict(claims)
    if alteration == "issuer":
        claims["iss"] = "other-issuer"
    elif alteration == "audience":
        claims["aud"] = "other-audience"
    elif alteration == "expired":
        claims["exp"] = int(datetime.now(timezone.utc).timestamp()) - 1
    token = jwt.encode(claims, "other-fixture-key-" + "q" * 64 if alteration == "signature" else key, algorithm="HS256")
    with TestClient(create_app(settings, registry)) as client:
        response = client.post("/api/v1/analysis-tasks", json=request_body(scope),
            headers={"Authorization": "Bearer " + token, "Idempotency-Key": uuid4().hex})
        assert response.status_code == 401 and token not in response.text


def test_scope_expansion_and_client_trusted_metadata_rejected(http_fixture):
    settings, registry, token, scope, _, _ = http_fixture
    with TestClient(create_app(settings, registry)) as client:
        headers = {"Authorization": "Bearer " + token, "Idempotency-Key": uuid4().hex}
        expanded = request_body(scope)
        expanded["scope"]["fields"] = ["status", "private-cost"]
        assert client.post("/api/v1/analysis-tasks", json=expanded, headers=headers).status_code == 403
        for key, value in [("tenantId", "other"), ("planVersion", "2"), ("snapshotId", "fake")]:
            body = dict(request_body(scope), **{key: value})
            assert client.post("/api/v1/analysis-tasks", json=body, headers=headers).status_code == 422
        body = dict(request_body(scope), scenarioId="S01")
        assert client.post("/api/v1/analysis-tasks", json=body, headers=headers).status_code == 422


def test_production_composition_never_registers_engineering_handler(http_fixture):
    settings, _, token, scope, _, _ = http_fixture
    with TestClient(create_app(settings)) as client:
        response = client.post("/api/v1/analysis-tasks", json=request_body(scope),
            headers={"Authorization": "Bearer " + token, "Idempotency-Key": uuid4().hex})
        assert response.status_code == 422 and response.json()["code"] == "UNSUPPORTED_SCENARIO"


def test_unauthenticated_task_request_has_no_anonymous_bypass(http_fixture):
    settings, registry, _, scope, _, _ = http_fixture
    with TestClient(create_app(settings, registry)) as client:
        assert client.post("/api/v1/analysis-tasks", json=request_body(scope),
                           headers={"Idempotency-Key": uuid4().hex}).status_code == 401
