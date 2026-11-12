"""G01 public current-policy checks. Errors contain fixed codes only, never JWT/key/DB text."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import re
import secrets
from urllib.parse import urlsplit

import jwt
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

from commerce_hub.governance.access.tables import grants, principals, sessions

SCOPE_DIMENSIONS = ("storeIds", "warehouseIds", "canonicalSkuIds", "fields")
ALLOWED_ACTIONS = frozenset({"tasks:create", "tasks:read", "tasks:cancel", "engineering:execute"})


class AccessDenied(RuntimeError):
    def __init__(self, code: str = "POLICY_DENIED"):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class Principal:
    tenant_id: str
    principal_id: str
    revision: int
    token_id: str


def _bounded_identifier(value):
    return isinstance(value, str) and 1 <= len(value) <= 64 and not any(ord(c) < 32 for c in value)


def _scope(scope, tenant_id):
    if not isinstance(scope, dict) or set(scope) != {"tenantId", *SCOPE_DIMENSIONS} or scope.get("tenantId") != tenant_id:
        raise AccessDenied()
    output = {"tenantId": tenant_id}
    for dimension in SCOPE_DIMENSIONS:
        values = scope[dimension]
        if not isinstance(values, list) or not 1 <= len(values) <= 100:
            raise AccessDenied()
        if any(not isinstance(v, str) or not 1 <= len(v) <= 128 or "*" in v or any(ord(c) < 32 for c in v) for v in values):
            raise AccessDenied()
        if len(set(values)) != len(values):
            raise AccessDenied()
        output[dimension] = tuple(values)
    return output


class AccessControl:
    def __init__(self, engine, issuer: str, audience: str, signing_key: str | bytes):
        key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
        if not issuer or not audience or not isinstance(key, bytes) or len(key) < 32:
            raise ValueError("AUTH_CONFIGURATION_INVALID")
        self.engine = engine
        self.issuer = issuer
        self.audience = audience
        self._key = key

    def authenticate(self, token: str) -> Principal:
        if not isinstance(token, str) or not 1 <= len(token) <= 8192:
            raise AccessDenied("UNAUTHENTICATED")
        try:
            claims = jwt.decode(token, self._key, algorithms=["HS256"], issuer=self.issuer, audience=self.audience,
                                options={"require": ["exp", "iat", "nbf", "sub", "tid", "jti", "rev"], "strict_aud": True})
            if any(not _bounded_identifier(claims[k]) for k in ["sub", "tid", "jti"]):
                raise AccessDenied("UNAUTHENTICATED")
            if any(type(claims[k]) is not int for k in ["exp", "iat", "nbf", "rev"]) or claims["rev"] < 1:
                raise AccessDenied("UNAUTHENTICATED")
            principal = Principal(claims["tid"], claims["sub"], claims["rev"], claims["jti"])
        except (jwt.PyJWTError, KeyError, TypeError, ValueError):
            raise AccessDenied("UNAUTHENTICATED") from None
        try:
            with self.engine.connect() as connection:
                self._assert_current(connection, principal, lock=False)
        except SQLAlchemyError:
            raise AccessDenied("AUTH_BACKEND_UNAVAILABLE") from None
        return principal

    def _assert_current(self, connection, principal: Principal, *, lock: bool):
        if not isinstance(principal, Principal):
            raise AccessDenied()
        principal_query = select(principals.c.active, principals.c.revision).where(
            principals.c.tenant_id == principal.tenant_id, principals.c.principal_id == principal.principal_id)
        session_query = select(sessions.c.active, sessions.c.expires_at).where(
            sessions.c.tenant_id == principal.tenant_id, sessions.c.principal_id == principal.principal_id,
            sessions.c.token_id == principal.token_id)
        if lock:
            principal_query = principal_query.with_for_update()
            session_query = session_query.with_for_update()
        current = connection.execute(principal_query).mappings().one_or_none()
        if not current or not current["active"] or current["revision"] != principal.revision:
            raise AccessDenied()
        session = connection.execute(session_query).mappings().one_or_none()
        now = connection.execute(select(func.utc_timestamp(6))).scalar_one()
        if not session or not session["active"] or session["expires_at"] <= now:
            raise AccessDenied()

    def authorize(self, connection, principal: Principal, action: str, scope: dict, *, lock: bool = True) -> None:
        """Called inside the owning command's transaction; locks serialize revocation with mutation."""
        if not isinstance(principal, Principal) or action not in ALLOWED_ACTIONS:
            raise AccessDenied()
        requested = _scope(scope, principal.tenant_id)
        try:
            self._assert_current(connection, principal, lock=lock)
            query = select(grants.c.scope).where(grants.c.tenant_id == principal.tenant_id,
                                                grants.c.principal_id == principal.principal_id,
                                                grants.c.action == action)
            if lock:
                query = query.with_for_update()
            grant = connection.execute(query).scalar_one_or_none()
            if grant is None:
                raise AccessDenied()
            allowed = _scope(grant, principal.tenant_id)
            if any(not set(requested[d]).issubset(allowed[d]) for d in SCOPE_DIMENSIONS):
                raise AccessDenied()
        except SQLAlchemyError:
            raise AccessDenied("AUTH_BACKEND_UNAVAILABLE") from None

    def issue_csrf(self, principal: Principal) -> str:
        nonce = secrets.token_urlsafe(32)
        return nonce + "." + self._csrf_mac(principal, nonce)

    def _csrf_mac(self, principal: Principal, nonce: str) -> str:
        message = json.dumps(["csrf-v1", principal.tenant_id, principal.principal_id, principal.revision,
                              principal.token_id, nonce], separators=(",", ":")).encode("utf-8")
        return hmac.new(self._key, message, hashlib.sha256).hexdigest()

    def validate_csrf(self, principal: Principal, cookie_token: str | None, header_token: str | None,
                      origin: str | None, expected_origin: str) -> None:
        expected = urlsplit(expected_origin)
        valid_origin = (expected.scheme in {"http", "https"} and bool(expected.netloc) and not expected.username
                        and expected.path == "" and not expected.query and not expected.fragment)
        if not valid_origin or (expected.scheme != "https" and expected.hostname not in {"127.0.0.1", "localhost", "::1"}):
            raise AccessDenied("CSRF_REJECTED")
        if origin != expected_origin or not isinstance(cookie_token, str) or not isinstance(header_token, str):
            raise AccessDenied("CSRF_REJECTED")
        pattern = r"[A-Za-z0-9_-]{43}\.[0-9a-f]{64}"
        if not re.fullmatch(pattern, cookie_token) or not re.fullmatch(pattern, header_token):
            raise AccessDenied("CSRF_REJECTED")
        if not hmac.compare_digest(cookie_token, header_token):
            raise AccessDenied("CSRF_REJECTED")
        nonce, supplied_mac = cookie_token.split(".")
        if not hmac.compare_digest(self._csrf_mac(principal, nonce), supplied_mac):
            raise AccessDenied("CSRF_REJECTED")

    def provision_fixture(self, connection, *, tenant_id: str, principal_id: str, token_id: str,
                          expires_at: datetime, grants_by_action: dict, revision: int = 1) -> Principal:
        """Explicit local/test fixture setup. No login endpoint or production account lifecycle is supplied."""
        if not all(_bounded_identifier(v) for v in [tenant_id, principal_id, token_id]) or type(revision) is not int or revision < 1:
            raise ValueError("INVALID_IDENTITY_FIXTURE")
        if expires_at.tzinfo is not None:
            expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
        if not grants_by_action or not set(grants_by_action).issubset(ALLOWED_ACTIONS):
            raise ValueError("INVALID_IDENTITY_FIXTURE")
        for scope in grants_by_action.values():
            _scope(scope, tenant_id)
        connection.execute(insert(principals).values(tenant_id=tenant_id, principal_id=principal_id, active=True, revision=revision))
        connection.execute(insert(sessions).values(tenant_id=tenant_id, principal_id=principal_id, token_id=token_id,
                                                   active=True, expires_at=expires_at))
        for action, scope in grants_by_action.items():
            connection.execute(insert(grants).values(tenant_id=tenant_id, principal_id=principal_id, action=action, scope=scope))
        return Principal(tenant_id, principal_id, revision, token_id)

    def revoke_token(self, connection, principal: Principal) -> None:
        # Same principal->session lock order as authorize prevents lock inversion.
        connection.execute(select(principals.c.revision).where(principals.c.tenant_id == principal.tenant_id,
                           principals.c.principal_id == principal.principal_id).with_for_update()).first()
        connection.execute(update(sessions).where(sessions.c.tenant_id == principal.tenant_id,
                           sessions.c.principal_id == principal.principal_id,
                           sessions.c.token_id == principal.token_id).values(active=False))

    def revoke_principal(self, connection, principal: Principal) -> None:
        connection.execute(update(principals).where(principals.c.tenant_id == principal.tenant_id,
                           principals.c.principal_id == principal.principal_id)
                           .values(active=False, revision=principals.c.revision + 1))
