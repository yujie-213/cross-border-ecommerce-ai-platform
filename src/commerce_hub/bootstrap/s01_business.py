"""Explicit synthetic S01 business workflow assembly, never a live-mode entry point."""
from decimal import Decimal
import sys

from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.entrypoints.http.app import create_app as app_factory
from commerce_hub.entrypoints.worker.__main__ import run
from commerce_hub.orchestration.service import HandlerSpec
from commerce_hub.scenarios.s01_supply_inventory import S01SupplyInventoryHandler


def registry(settings):
    if (settings.environment != "test" or settings.model_provider != "mock"
            or settings.model_network_enabled):
        raise ValueError("S01_BUSINESS_REQUIRES_OFFLINE_MOCK_TEST_ENVIRONMENT")
    spec = HandlerSpec("ENGINEERING_S01_BUSINESS", "0.1.0", "s01.business.v1",
        S01SupplyInventoryHandler(timeout_seconds=settings.model_timeout_seconds),
        max_calls=1, max_tokens=24000, max_cost=Decimal(".01"),
        policy_version="s01-business-mock-v1")
    return {spec.scenario_id: spec}


def create_app():
    settings = load_settings()
    return app_factory(settings, registry(settings))


if __name__ == "__main__":
    if sys.argv[1:] != ["worker"]:
        raise SystemExit("Use the explicit S01 offline business worker command")
    settings = load_settings()
    raise SystemExit(run(settings, registry(settings)))
