"""Explicit V2 teaching assembly; startup performs no ERP IO or migration."""
from pathlib import Path
from decimal import Decimal
import json,os,sys,hashlib
from dotenv import dotenv_values
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.infrastructure.database import Database,assert_migration_target
from commerce_hub.data.sync.v2 import V2Reader
from commerce_hub.data.sync.v2_store import AcquisitionCheckpoint
from commerce_hub.adapters.erp import ERPConfig,https_transport,AUTH_PATH
from commerce_hub.adapters.erp_requisition import TeachingRequisitionClient
from commerce_hub.data.projection.monitor import MonitorRegistry
from commerce_hub.scenarios.s01_v2.handler import V2Handler
from commerce_hub.scenarios.s01_v2.policy import V2Policy
from commerce_hub.orchestration.service import HandlerSpec,SharedModelAuthorization
from commerce_hub.entrypoints.http.app import create_app as app_factory
from commerce_hub.entrypoints.worker.__main__ import run

ROOT=Path(__file__).resolve().parents[3]


def erp_config():
    v=dotenv_values(ROOT/'.env.erp',interpolate=False)
    return ERPConfig(username=v.get('ERP_USERNAME') or '',password=v.get('ERP_PASSWORD') or '',access_token=v.get('ERP_ACCESS_TOKEN') or '',timeout=8,interval=.65)


def registry(settings):
    if settings.environment!='test' or os.environ.get('COMMERCE_S01_V2_ENABLED')!='true':raise ValueError('EXPLICIT_V2_TEACHING_MODE_REQUIRED')
    assert_migration_target(settings)
    db=Database(settings)
    app_tenant=os.environ.get('COMMERCE_S01_V2_APP_TENANT','s01-v2-teaching-local')
    policy=V2Policy(app_tenant,os.environ.get('COMMERCE_S01_V2_SOURCE_TENANT','1'),
        owned_mappings=MonitorRegistry(db.engine,'s01-owned-teaching-local').mappings(),
        owned_provider=lambda:MonitorRegistry(db.engine,'s01-owned-teaching-local').mappings(),
        requisition_enabled=os.environ.get('COMMERCE_S01_V2_REQUISITION_ENABLED')=='true',owned_only=True)
    def reader_factory(context):
        root=ROOT/'data/private/s01-v2'/context.task['tenant_id']/context.task['task_id']
        return V2Reader(erp_config(),root,AcquisitionCheckpoint(context),context.check,
            request_limit=int(os.environ.get('COMMERCE_S01_V2_REQUEST_LIMIT','400')))
    provider=None;shared=None
    if os.environ.get('COMMERCE_S01_V2_MODEL_ENABLED')=='true':
        from commerce_hub.adapters.models.online import OnlineDeepSeekProvider,V2_AUTHORIZATION_ID,EXPERIENCE_AUTHORIZATION_ID,WORKFLOW_AUTHORIZATION_ID,DAILY_USE_AUTHORIZATION_ID
        if settings.model_provider!='deepseek' or not settings.model_network_enabled or settings.model_max_output_tokens!=1024:raise ValueError('V2_MODEL_CONFIGURATION_INVALID')
        authorization=os.environ.get('COMMERCE_S01_V2_MODEL_AUTHORIZATION',V2_AUTHORIZATION_ID)
        if authorization not in {V2_AUTHORIZATION_ID,EXPERIENCE_AUTHORIZATION_ID,WORKFLOW_AUTHORIZATION_ID,DAILY_USE_AUTHORIZATION_ID}:raise ValueError('V2_MODEL_AUTHORIZATION_INVALID')
        provider=OnlineDeepSeekProvider(settings,ROOT/'data/private/s01-v2-model',authorization_id=authorization)
        # Daily use has no cumulative call/token/cost cap (owner request 2026-11-15).
        # Old validation usage/reservations stay on their original policy.
        shared=SharedModelAuthorization(authorization,None,None,None) if authorization in {EXPERIENCE_AUTHORIZATION_ID,DAILY_USE_AUTHORIZATION_ID} else SharedModelAuthorization(authorization,4,96000,Decimal('.20'))
    elif settings.model_network_enabled:raise ValueError('V2_MODEL_NOT_EXPLICITLY_ENABLED')
    batch=V2Handler(db.engine,policy,reader_factory)
    # Exact-ID purchase tracking is read-only and stays available with writes off.
    from commerce_hub.adapters.erp import TeachingERPReader
    batch.purchase_reader_factory=lambda: TeachingERPReader(erp_config())
    single=V2Handler(db.engine,policy,reader_factory,single=True,provider=provider)
    if policy.requisition_enabled:
        def client_factory(operation,check):
            folder=ROOT/'data/private/s01-v2-requisitions'/operation
            folder.mkdir(parents=True,exist_ok=True)
            def transport(method,target,headers,body,config):
                check()
                status,raw=https_transport(method,target,headers,body,config)
                if target!=AUTH_PATH:
                    digest=hashlib.sha256(raw).hexdigest();(folder/(digest+'.json')).write_bytes(raw)
                    with (folder/'requests.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(method=method,path=target.split('?')[0],httpStatus=status,sha256=digest))+'\n')
                return status,raw
            return TeachingRequisitionClient(erp_config(),transport=transport)
        single.requisition_client_factory=client_factory
        single.requisition_private_root=ROOT/'data/private/s01-v2-requisitions'
    return dict(S01_V2_BATCH=HandlerSpec('S01_V2_BATCH','0.1.0','s01.product.batch.v1',batch),
        S01_V2_SINGLE=HandlerSpec('S01_V2_SINGLE','0.1.0','s01.product.single.v1',single,
            max_calls=1 if provider else 0,max_tokens=24000 if provider else 0,max_cost=Decimal('.05') if provider else Decimal('0'),
            policy_version=shared.authorization_id if shared else 's01-v2-no-model-v1',cost_currency='USD' if provider else None,shared_model_authorization=shared))


def create_app():
    settings=load_settings();return app_factory(settings,registry(settings))


if __name__=='__main__':
    if sys.argv[1:]!=['worker']:raise SystemExit('Explicit worker command required')
    settings=load_settings();raise SystemExit(run(settings,registry(settings)))
