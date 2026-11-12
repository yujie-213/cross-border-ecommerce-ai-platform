"""Test-only assembly for a deterministic kill during a running S01 task."""
import os
import sys
import time

from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.entrypoints.http.app import create_app as app_factory
from commerce_hub.entrypoints.worker.__main__ import run
from commerce_hub.orchestration.service import HandlerSpec
from commerce_hub.scenarios.s01 import S01EngineeringHandler


class DelayedHandler(S01EngineeringHandler):
    def run(self, context, parameters):
        end = time.monotonic() + float(os.environ.get("COMMERCE_S01_TEST_DELAY", "0"))
        while time.monotonic() < end:
            context.check()
            time.sleep(0.05)
        return super().run(context, parameters)


def registry(settings):
    if settings.environment != "test":
        raise ValueError("TEST_ASSEMBLY_REQUIRES_TEST_ENVIRONMENT")
    spec = HandlerSpec("ENGINEERING_S01", "0.1.0", os.environ["COMMERCE_FIXTURE_KIND"], DelayedHandler(),
                       policy_version="engineering-demo-v1")
    return {spec.scenario_id: spec}


def create_app():
    settings = load_settings()
    return app_factory(settings, registry(settings))


if __name__ == "__main__":
    if sys.argv[1:] != ["worker"]:
        raise SystemExit("Only the explicit test worker command is supported")
    settings = load_settings()
    raise SystemExit(run(settings, registry(settings)))
