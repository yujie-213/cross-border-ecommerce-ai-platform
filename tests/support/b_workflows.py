"""Engineering-only assembly: production B/S01 handlers, explicit synthetic ERP.

Never loaded by the daily launcher. No external model or ERP connection exists.
"""
import os
import sys
import time
from dataclasses import replace
from pathlib import Path

from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.bootstrap.after_sales import registry as b_registry
from commerce_hub.entrypoints.http.app import create_app as factory
from commerce_hub.infrastructure.database import Database
from commerce_hub.orchestration.service import HandlerSpec
from commerce_hub.scenarios.s01_v2.handler import V2Handler
from commerce_hub.scenarios.s01_v2.policy import V2Policy
from commerce_hub.data.sync.v2_store import AcquisitionCheckpoint
from commerce_hub.scenarios.after_sales.source import SourceReader
from commerce_hub.adapters.erp import TeachingERPReader,ERPConfig
from tests.support.b_source import BSourceERP


def registry(settings):
    if settings.environment!='test' or not os.environ.get('B_WORKFLOW_TEST_TENANT'):
        raise ValueError('EXPLICIT_TEST_ASSEMBLY_REQUIRED')
    specs=b_registry(settings)
    source=BSourceERP()
    reader=SourceReader(lambda:TeachingERPReader(ERPConfig(access_token='synthetic-source-token'),transport=source.transport),
        {'Synthetic Store':dict(sourceTenant='1',storeId='1')},Path('.tmp/b-process-private'))
    for sid,spec in list(specs.items()):
        specs[sid]=replace(spec,work_kind='b-test.'+settings.local_app_tenant+'.'+spec.handler.job)
        spec.handler.provider=None
        spec.handler.source_reader=reader
    delay=float(os.environ.get('B_WORKFLOW_TEST_DELAY','0'))
    if delay:
        h=specs['B_DATASET_VALIDATE_V1'].handler;original=h.run
        def delayed(context,parameters):
            stop=time.monotonic()+delay
            while time.monotonic()<stop:context.check();time.sleep(.05)
            return original(context,parameters)
        h.run=delayed
    database=Database(settings)
    policy=V2Policy(settings.local_app_tenant,'1')
    def read(context):return source.reader(Path('.tmp/b-process-private')/context.task['task_id'],AcquisitionCheckpoint(context),context.check)
    for sid,single in [('S01_V2_BATCH',False),('S01_V2_SINGLE',True)]:
        specs[sid]=HandlerSpec(sid,'0.1.0','b-v1-integration.'+sid,V2Handler(database.engine,policy,read,single=single))
    return specs


def create_app():
    settings=load_settings()
    return factory(settings,registry(settings))


if __name__=='__main__':
    if sys.argv[1:]!=['worker']:raise SystemExit('Explicit test Worker command required')
    from commerce_hub.entrypoints.worker.__main__ import run
    settings=load_settings()
    raise SystemExit(run(settings,registry(settings)))
