"""ONLY tests register this engineering handler. Production composition stays empty."""
from decimal import Decimal
import os
import sys
import time

from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.entrypoints.http.app import create_app as production_app
from commerce_hub.entrypoints.worker.__main__ import run
from commerce_hub.orchestration.service import HandlerSpec
from commerce_hub.orchestration.worker import RetryableStep


class EngineeringHandler:
    def validate(self, parameters):
        if not isinstance(parameters, dict) or set(parameters) - {"delaySeconds", "failUntilAttempt"}:
            raise ValueError("INVALID_FIXTURE_PARAMETERS")
        if type(parameters.get("delaySeconds", 0)) not in [int, float] or not 0 <= parameters.get("delaySeconds", 0) <= 5:
            raise ValueError("INVALID_FIXTURE_DELAY")
        if type(parameters.get("failUntilAttempt", 0)) is not int or not 0 <= parameters.get("failUntilAttempt", 0) <= 3:
            raise ValueError("INVALID_FIXTURE_RETRY")

    def run(self, context, parameters):
        end = time.monotonic() + parameters.get("delaySeconds", 0)
        while time.monotonic() < end:
            context.check()
            time.sleep(0.05)
        if context.lease.attempt <= parameters.get("failUntilAttempt", 0):
            raise RetryableStep("ENGINEERING_FIXTURE_FAILURE")
        context.check()


def registry():
    if os.environ.get("COMMERCE_ENVIRONMENT") != "test":
        raise RuntimeError("TEST_ASSEMBLY_REQUIRES_TEST_ENVIRONMENT")
    spec = HandlerSpec("ENGINEERING_FIXTURE", "1", os.environ["COMMERCE_FIXTURE_KIND"], EngineeringHandler(),
                       max_calls=2, max_tokens=100, max_cost=Decimal("1"), policy_version="simulated-engineering-v1")
    return {spec.scenario_id: spec}


def create_app():
    return production_app(load_settings(), registry())


if __name__ == "__main__":
    if sys.argv[1:] != ["worker"]:
        raise SystemExit("Only the explicit test worker command is supported")
    raise SystemExit(run(load_settings(), registry()))
