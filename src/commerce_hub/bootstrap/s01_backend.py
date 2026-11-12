"""Explicit fixed-catalog backend API and independent worker; no network on startup."""
import json
import os
from pathlib import Path
import sys
from decimal import Decimal

from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.entrypoints.http.app import create_app as app_factory
from commerce_hub.entrypoints.worker.__main__ import run
from commerce_hub.orchestration.service import HandlerSpec
from commerce_hub.scenarios.s01_backend import S01BackendHandler
from commerce_hub.scenarios.s01_supply_inventory import S01MockProvider
from commerce_hub.data.contracts import fingerprint


def registry(settings, packages=None):
    if settings.environment != "test" or settings.model_provider != "mock" or settings.model_network_enabled:
        raise ValueError("BACKEND_REQUIRES_EXPLICIT_TEST_OFFLINE_ENVIRONMENT")
    if packages is None:
        configured = os.environ.get("COMMERCE_S01_CATALOG_PATH")
        if not configured:
            raise ValueError("BACKEND_CATALOG_REQUIRED")
        try:
            packages = json.loads(Path(configured).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ValueError("BACKEND_CATALOG_NOT_AVAILABLE") from None
    use_mock = os.environ.get("COMMERCE_S01_EXPLANATION_MODE", "off") == "mock"
    revision = fingerprint(dict(packages=packages, mock=use_mock, issuer=settings.auth_issuer, audience=settings.auth_audience))
    spec = HandlerSpec("S01_BACKEND", "0.1.0", "s01.backend.v1." + revision[:32],
        S01BackendHandler(packages, provider=S01MockProvider() if use_mock else None,
            timeout_seconds=settings.model_timeout_seconds),
        max_calls=1 if use_mock else 0, max_tokens=24000 if use_mock else 0,
        max_cost=Decimal(".01") if use_mock else Decimal("0"), policy_version="s01-backend-readonly-v1", cost_currency="TEST")
    return {spec.scenario_id: spec}


def create_app():
    settings = load_settings()
    return app_factory(settings, registry(settings))


if __name__ == "__main__":
    if sys.argv[1:] != ["worker"]:
        raise SystemExit("Use the explicit S01 backend worker command")
    settings = load_settings()
    raise SystemExit(run(settings, registry(settings)))
