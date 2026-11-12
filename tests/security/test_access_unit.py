"""Pure token/scope/CSRF checks. Database policy tests are separate, never SQLite substitutes."""
from dataclasses import FrozenInstanceError
import time

import jwt
import pytest
from sqlalchemy.exc import OperationalError

from commerce_hub.governance.access import AccessControl, AccessDenied, Principal
from commerce_hub.governance.access.service import _scope

KEY = "fixture-signing-key-only-" + "x" * 64
ISSUER = "https://fixture-issuer.invalid"
AUDIENCE = "commerce-fixture"


class NoDatabase:
    def connect(self):
        return self

    def __enter__(self):
        return object()

    def __exit__(self, *_):
        return False


@pytest.fixture
def access(monkeypatch):
    service = AccessControl(NoDatabase(), ISSUER, AUDIENCE, KEY)
    monkeypatch.setattr(service, "_assert_current", lambda *_args, **_kwargs: None)
    return service


def claims(**changes):
    now = int(time.time())
    values = dict(iss=ISSUER, aud=AUDIENCE, sub="user-fixture", tid="tenant-fixture", jti="token-fixture",
                  exp=now + 600, iat=now, nbf=now, rev=1)
    values.update(changes)
    return values


def scope():
    return {"tenantId": "tenant-fixture", "storeIds": ["store-fixture"], "warehouseIds": ["warehouse-fixture"],
            "canonicalSkuIds": ["sku-fixture"], "fields": ["inventory"]}


def test_valid_signed_identity_is_immutable(access):
    principal = access.authenticate(jwt.encode(claims(), KEY, algorithm="HS256"))
    assert principal == Principal("tenant-fixture", "user-fixture", 1, "token-fixture")
    with pytest.raises(FrozenInstanceError):
        principal.tenant_id = "other"


@pytest.mark.parametrize("changes", [{"iss": "other"}, {"aud": "other"}, {"aud": [AUDIENCE, "other"]},
                                     {"exp": 1}, {"nbf": 4102444800}, {"iat": 4102444800},
                                     {"tid": ""}, {"jti": 7}, {"rev": True}, {"rev": 0}, {"exp": 4102444800.5}])
def test_invalid_claims_rejected_without_echo(access, changes):
    token = jwt.encode(claims(**changes), KEY, algorithm="HS256")
    with pytest.raises(AccessDenied) as error:
        access.authenticate(token)
    assert token not in str(error.value)
    assert KEY not in str(error.value)


@pytest.mark.parametrize("claim", ["exp", "iat", "nbf", "sub", "tid", "jti", "rev"])
def test_required_claims(access, claim):
    values = claims()
    values.pop(claim)
    with pytest.raises(AccessDenied):
        access.authenticate(jwt.encode(values, KEY, algorithm="HS256"))


def test_wrong_signature_algorithm_and_malformed_token(access):
    for token in [jwt.encode(claims(), KEY + "other", algorithm="HS256"),
                  jwt.encode(claims(), KEY, algorithm="HS512"),
                  jwt.encode(claims(), None, algorithm="none"), "bad-token", ""]:
        with pytest.raises(AccessDenied):
            access.authenticate(token)


@pytest.mark.parametrize("dimension", ["storeIds", "warehouseIds", "canonicalSkuIds", "fields"])
def test_empty_or_wildcard_scope_never_means_all(dimension):
    for value in [[], ["*"], ["duplicate", "duplicate"], "unbounded", ["x"] * 101]:
        data = scope()
        data[dimension] = value
        with pytest.raises(AccessDenied):
            _scope(data, "tenant-fixture")


def test_scope_unknown_dimension_or_cross_tenant_rejected():
    for data in [dict(scope(), tenantId="other"), dict(scope(), role="admin"), {"tenantId": "tenant-fixture"}]:
        with pytest.raises(AccessDenied):
            _scope(data, "tenant-fixture")


def test_csrf_is_same_origin_and_bound_to_identity(access):
    principal = Principal("tenant-fixture", "user-fixture", 1, "token-fixture")
    token = access.issue_csrf(principal)
    access.validate_csrf(principal, token, token, "https://fixture.example", "https://fixture.example")
    for cookie, header, origin in [(None, token, "https://fixture.example"), (token, None, "https://fixture.example"),
                                   (token, token, "https://attacker.invalid"), (token, token[:-1] + "z", "https://fixture.example"),
                                   ("非ASCII", "非ASCII", "https://fixture.example")]:
        with pytest.raises(AccessDenied):
            access.validate_csrf(principal, cookie, header, origin, "https://fixture.example")
    with pytest.raises(AccessDenied):
        access.validate_csrf(Principal("other", "user-fixture", 1, "token-fixture"), token, token,
                             "https://fixture.example", "https://fixture.example")
    with pytest.raises(AccessDenied):
        access.validate_csrf(principal, token, token, "http://remote.invalid", "http://remote.invalid")


def test_authorize_rejects_nonprincipal_without_database(access):
    with pytest.raises(AccessDenied):
        access.authorize(None, None, "tasks:create", scope())


def test_backend_failure_does_not_render_driver_secrets():
    secret = "fixture-only-sensitive-driver-error"
    class UnavailableDatabase:
        def connect(self):
            raise OperationalError("fixture statement", {"password": secret}, RuntimeError(secret))
    service = AccessControl(UnavailableDatabase(), ISSUER, AUDIENCE, KEY)
    with pytest.raises(AccessDenied) as error:
        service.authenticate(jwt.encode(claims(), KEY, algorithm="HS256"))
    assert error.value.code == "AUTH_BACKEND_UNAVAILABLE"
    assert secret not in str(error.value)
