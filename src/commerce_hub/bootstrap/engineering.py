"""Opt-in local/test engineering assembly; default application remains closed."""
import sys
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.entrypoints.http.app import create_app as app_factory
from commerce_hub.entrypoints.worker.__main__ import run
from commerce_hub.orchestration.service import HandlerSpec
from commerce_hub.scenarios.s01 import S01EngineeringHandler


def registry(settings):
    if settings.environment != "test":
        raise ValueError("ENGINEERING_ASSEMBLY_REQUIRES_TEST_ENVIRONMENT")
    spec = HandlerSpec("ENGINEERING_S01", "0.1.0", "s01.engineering.v1", S01EngineeringHandler(),
                       policy_version="engineering-demo-v1")
    return {spec.scenario_id: spec}


def create_app():
    settings = load_settings()
    return app_factory(settings, registry(settings))


if __name__ == "__main__":
    if sys.argv[1:] != ["worker"]:
        raise SystemExit("Use the explicit engineering worker command")
    settings = load_settings()
    raise SystemExit(run(settings, registry(settings)))
