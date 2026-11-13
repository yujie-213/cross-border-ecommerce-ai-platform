"""Explicit ONLINE_TEACHING_ERP assembly; startup/options never perform source IO."""
import json
import os
from pathlib import Path
import sys
from dotenv import dotenv_values
from commerce_hub.adapters.erp import ERPConfig,TeachingERPReader,https_transport,AUTH_PATH
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.data.sync.online import OnlineMapping
from commerce_hub.data.contracts import fingerprint
from commerce_hub.scenarios.s01_backend.online import OnlineS01Handler
from commerce_hub.orchestration.service import HandlerSpec
from commerce_hub.entrypoints.http.app import create_app as app_factory
from commerce_hub.entrypoints.worker.__main__ import run

ROOT=Path(__file__).resolve().parents[3]

def registry(settings):
    if settings.environment != 'test' or os.environ.get('COMMERCE_S01_ONLINE_ENABLED') != 'true':
        raise ValueError('EXPLICIT_TEACHING_ONLINE_MODE_REQUIRED')
    path=Path(os.environ.get('COMMERCE_S01_ONLINE_MAPPING_PATH','')).resolve()
    if not path.is_relative_to((ROOT/'data/private').resolve()):
        raise ValueError('PRIVATE_ONLINE_MAPPING_REQUIRED')
    mappings=[OnlineMapping.model_validate(m).validate_scope() for m in json.loads(path.read_text(encoding='utf-8'))]
    def reader_factory(context,acquisition_id):
        values=dotenv_values(ROOT/'.env.erp',interpolate=False)
        config=ERPConfig(base_url=values.get('ERP_BASE_URL') or 'https://47.107.76.124/lingxing-erp',
            username=values.get('ERP_USERNAME') or '',password=values.get('ERP_PASSWORD') or '',
            access_token=values.get('ERP_ACCESS_TOKEN') or '',timeout=8,max_requests=48)
        private=ROOT/'data/private/s01-online'/context.task['tenant_id']/context.task['task_id']/acquisition_id
        private.mkdir(parents=True,exist_ok=False)
        serial=[0]
        def transport(method,target,headers,body,config):
            context.check()
            status,raw=https_transport(method,target,headers,body,config)
            if not target.startswith(AUTH_PATH):
                serial[0]+=1
                (private/f'response-{serial[0]:03d}.json').write_bytes(raw)
            context.check()
            return status,raw
        return TeachingERPReader(config,transport=transport)
    if settings.model_network_enabled or settings.model_provider != 'mock':
        raise ValueError('ONLINE_MODEL_NOT_ENABLED_IN_PHASE1')
    revision=fingerprint([m.model_dump(mode='json') for m in mappings])
    handler=OnlineS01Handler(mappings,reader_factory)
    spec=HandlerSpec('S01_BACKEND','0.1.0','s01.online.v1.'+revision[:32],handler,
        policy_version='s01-online-readonly-v1')
    return {spec.scenario_id:spec}

def create_app():
    settings=load_settings()
    return app_factory(settings,registry(settings))

if __name__=='__main__':
    if sys.argv[1:] != ['worker']:raise SystemExit('Explicit online worker command required')
    settings=load_settings()
    raise SystemExit(run(settings,registry(settings)))
