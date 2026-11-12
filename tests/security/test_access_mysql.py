"""Real MySQL current policy/revocation checks; enabled only by explicit engineering test flag."""
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import os
from threading import Event
import time
from uuid import uuid4

import jwt
import pytest
from sqlalchemy import delete, update

from commerce_hub.governance.access import AccessControl, AccessDenied
from commerce_hub.governance.access.tables import grants, principals, sessions

pytestmark = [pytest.mark.mysql, pytest.mark.skipif(os.environ.get("COMMERCE_RUN_MYSQL_TESTS") != "1",
                                                  reason="Real MySQL engineering tests are opt-in")]
KEY = "fixture-signing-key-only-" + "x" * 64
ISSUER, AUDIENCE = "https://fixture-issuer.invalid", "commerce-fixture"


@pytest.fixture
def auth_fixture(database):
    service = AccessControl(database.engine, ISSUER, AUDIENCE, KEY)
    tenant, user, token_id = "auth-" + uuid4().hex, "user-fixture", uuid4().hex
    scope = {"tenantId": tenant, "storeIds": ["store-fixture"], "warehouseIds": ["warehouse-fixture"],
             "canonicalSkuIds": ["sku-fixture"], "fields": ["inventory"]}
    with database.engine.begin() as connection:
        principal = service.provision_fixture(connection, tenant_id=tenant, principal_id=user, token_id=token_id,
                       expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                       grants_by_action={"tasks:create": scope, "tasks:read": scope, "tasks:cancel": scope})
    now = int(time.time())
    token = jwt.encode(dict(iss=ISSUER, aud=AUDIENCE, sub=user, tid=tenant, jti=token_id, rev=1,
                            iat=now, nbf=now, exp=now + 3600), KEY, algorithm="HS256")
    yield service, principal, token, scope
    with database.engine.begin() as connection:
        # Delete only this test's unique tenant fixture, never a shared/project record.
        connection.execute(delete(sessions).where(sessions.c.tenant_id == tenant))
        connection.execute(delete(grants).where(grants.c.tenant_id == tenant))
        connection.execute(delete(principals).where(principals.c.tenant_id == tenant))


def test_real_current_identity_scope_and_field_limits(database, auth_fixture):
    service, principal, token, scope = auth_fixture
    assert service.authenticate(token) == principal
    with database.engine.begin() as connection:
        service.authorize(connection, principal, "tasks:create", scope)
        for expanded in [dict(scope, tenantId="other-tenant"), dict(scope, storeIds=["other-store"]),
                         dict(scope, canonicalSkuIds=["other-sku"]), dict(scope, fields=["supplier_secret"]),
                         dict(scope, fields=[])]:
            with pytest.raises(AccessDenied):
                service.authorize(connection, principal, "tasks:read", expanded)
        with pytest.raises(AccessDenied):
            service.authorize(connection, principal, "engineering:execute", scope)


def test_real_token_revocation_invalidates_old_actor_on_next_check(database, auth_fixture):
    service, principal, token, scope = auth_fixture
    with database.engine.begin() as connection:
        service.revoke_token(connection, principal)
    with pytest.raises(AccessDenied):
        service.authenticate(token)
    with database.engine.begin() as connection:
        with pytest.raises(AccessDenied):
            service.authorize(connection, principal, "tasks:cancel", scope)


def test_real_principal_revision_and_grant_changes_rechecked(database, auth_fixture):
    service, principal, token, scope = auth_fixture
    with database.engine.begin() as connection:
        connection.execute(update(grants).where(grants.c.tenant_id == principal.tenant_id,
                           grants.c.action == "tasks:read").values(scope=dict(scope, fields=["different-field"])))
    with database.engine.begin() as connection:
        with pytest.raises(AccessDenied):
            service.authorize(connection, principal, "tasks:read", scope)
        service.revoke_principal(connection, principal)
    with pytest.raises(AccessDenied):
        service.authenticate(token)


def test_real_session_expiry_is_rechecked_even_while_jwt_valid(database, auth_fixture):
    service, principal, token, scope = auth_fixture
    with database.engine.begin() as connection:
        connection.execute(update(sessions).where(sessions.c.tenant_id == principal.tenant_id,
                           sessions.c.token_id == principal.token_id)
                           .values(expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=1)))
    with pytest.raises(AccessDenied):
        service.authenticate(token)
    with database.engine.begin() as connection:
        with pytest.raises(AccessDenied):
            service.authorize(connection, principal, "tasks:read", scope)


def test_real_revocation_serializes_with_authorized_mutation(database, auth_fixture):
    service, principal, token, scope = auth_fixture
    entered = Event()
    def revoke():
        with database.engine.begin() as connection:
            entered.set()
            service.revoke_token(connection, principal)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with database.engine.begin() as connection:
            service.authorize(connection, principal, "tasks:cancel", scope, lock=True)
            pending = pool.submit(revoke)
            assert entered.wait(5)
            # A concurrent revocation cannot cross this command's authorization linearization point.
            time.sleep(0.1)
            assert not pending.done()
        pending.result(timeout=5)
    with pytest.raises(AccessDenied):
        service.authenticate(token)
