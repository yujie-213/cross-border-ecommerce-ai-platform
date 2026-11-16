"""Test-only B assembly. No production B scenarios, ERP or model clients are registered."""
import os
import sys
import time
from decimal import Decimal

from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.entrypoints.http.app import create_app as factory
from commerce_hub.entrypoints.worker.__main__ import run
from commerce_hub.orchestration.b_authorization import BTaskAuthorization
from commerce_hub.orchestration.service import HandlerSpec
from tests.support.foundation import EngineeringHandler


class DelayedBFixture(EngineeringHandler):
    def run(self, context, parameters):
        end = time.monotonic() + 1.8
        while time.monotonic() < end:
            context.check()
            time.sleep(.05)


def registry():
    if os.environ.get('COMMERCE_ENVIRONMENT') != 'test':
        raise ValueError('TEST_ASSEMBLY_REQUIRED')
    spec = HandlerSpec('B_FIXTURE', '1', os.environ['COMMERCE_FIXTURE_KIND'], DelayedBFixture(),
        max_calls=2, max_tokens=100, max_cost=Decimal('1'),
        task_authorization=BTaskAuthorization('CASE', 'b:analyze'))
    return {spec.scenario_id: spec}


def create_app():
    return factory(load_settings(), registry())


if __name__ == '__main__':
    if sys.argv[1:] != ['worker']:
        raise SystemExit('Explicit fixture worker command required')
    raise SystemExit(run(load_settings(), registry()))
