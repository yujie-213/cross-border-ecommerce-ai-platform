"""Real isolated MySQL/O01/G01 with synthetic ERP; never live acceptance."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from threading import Event
from types import SimpleNamespace
from uuid import uuid4
import json
import pytest
from sqlalchemy import select,update,insert,func
from commerce_hub.governance.access.tables import grants
from commerce_hub.orchestration.service import HandlerSpec,TaskError
from commerce_hub.orchestration.worker import Worker,ExecutionContext
from commerce_hub.orchestration.tables import budgets
from commerce_hub.infrastructure.work import LeaseLost
from commerce_hub.infrastructure.work_tables import work_items
from commerce_hub.data.sync.v2_store import AcquisitionCheckpoint,acquisitions
from commerce_hub.adapters.erp import ERPConfig
from commerce_hub.adapters.erp_requisition import TeachingRequisitionClient
from commerce_hub.capabilities.models.contracts import ProviderResult,Usage
from commerce_hub.scenarios.s01_v2.handler import V2Handler,collection_scope
from commerce_hub.scenarios.s01_v2.policy import V2Policy
from commerce_hub.scenarios.s01_v2.store import ItemStore
from commerce_hub.scenarios.s01_v2.requisition import V2RequisitionService
from tests.integration.orchestration.test_s01_reports import make_s01
from tests.support.v2 import SyntheticERP

pytestmark=pytest.mark.mysql


class SyntheticModel:
    calls=0
    def describe_capabilities(self):return {'structured_output'}
    def preflight(self,payload,cost):pass
    def invoke(self,request):
        self.calls+=1
        facts=json.loads(request.payload.messages[-1].content)['facts']
        output={k:[] for k in ['recommendationReasons','keyEvidence','majorRisks','humanConfirmations']}
        for f in facts:
            for section in f['requiredSections']:output[section].append(dict(text=f['allowedPhrases'][0],supportRefs=[f['ref']]))
        return ProviderResult(status='COMPLETED',finishReason='stop',content=json.dumps(output,ensure_ascii=False),
            actualModelRevision='deepseek-flash',usage=Usage(inputTokens=100,outputTokens=50,actualCost=Decimal('.0001'),currency='TEST',pricingVersion='synthetic-v1'))


def environment(make_s01,tmp_path,count=5,model=None):
    e=make_s01();e.scope=collection_scope(e.tenant);e.erp=SyntheticERP(count)
    with e.database.engine.begin() as c:
        c.execute(update(grants).where(grants.c.tenant_id==e.tenant).values(scope=e.scope))
        c.execute(insert(grants).values(tenant_id=e.tenant,principal_id=e.principal.principal_id,action='s01:requisition',scope=e.scope))
    owned=SimpleNamespace(sourceTenant='1',sourceStore='1',sourceWarehouse='1',
        monitor=SimpleNamespace(productId='1',datasetId='synthetic-owned',scopeVersion=1,importBatchId='synthetic-batch'))
    e.policy=V2Policy(e.tenant,'1',owned_mappings=[owned],requisition_enabled=True)
    def reader(context):return e.erp.reader(tmp_path/context.task['task_id'],AcquisitionCheckpoint(context),context.check)
    e.batch=V2Handler(e.database.engine,e.policy,reader)
    e.single=V2Handler(e.database.engine,e.policy,reader,single=True,provider=model)
    e.service.registry={s.scenario_id:s for s in [HandlerSpec('S01_V2_BATCH','0.1.0','v2.batch.'+uuid4().hex,e.batch),
        HandlerSpec('S01_V2_SINGLE','0.1.0','v2.single.'+uuid4().hex,e.single,max_calls=1 if model else 0,max_tokens=24000 if model else 0,max_cost=Decimal('.05') if model else Decimal('0'),cost_currency='TEST')]}
    e.create=lambda:e.service.create(e.principal,'batch','S01_V2_BATCH',e.scope,{},'synthetic')
    e.private_root=tmp_path
    return e


def run(e):
    view=e.create();assert Worker(e.service).once()
    tid=view['taskRef']['taskId']
    assert e.service.read(e.principal,tid)['state']=='SUCCEEDED'
    return tid,e.service.read_report(e.principal,tid)


def test_1000_real_mysql_batch_zero_models_zero_mutations_complete_history_and_replay(make_s01,tmp_path):
    e=environment(make_s01,tmp_path,1000);tid,report=run(e)
    summary=report['dataReport']['summary']
    assert summary['discoveredSkuCount']==summary['processedCount']==summary['erpReference']==1000
    assert report['dataReport']['enumerationComplete'] is True and e.erp.mutations==0
    with e.database.engine.connect() as c:
        budget=c.execute(select(budgets).filter_by(tenant_id=e.tenant,task_id=tid)).mappings().one()
        acq=c.execute(select(acquisitions).filter_by(tenant_id=e.tenant,task_id=tid)).mappings().one()
    assert budget['used_calls']==budget['reserved_calls']==0 and acq['request_count']<40
    assert e.create()['taskRef']['taskId']==tid
    assert len(e.service.history(e.principal,e.scope,scenario_id='S01_V2_BATCH')['items'])==1


def test_crash_after_partial_results_resumes_same_task_and_request_budget(make_s01,tmp_path,monkeypatch):
    import commerce_hub.scenarios.s01_v2.handler as h
    e=environment(make_s01,tmp_path,1000);tid=e.create()['taskRef']['taskId']
    lease=e.queue.claim([e.service.registry['S01_V2_BATCH'].work_kind]);row=e.service.start(lease,e.principal)
    ctx=ExecutionContext(e.service,lease,e.principal,row,Event())
    original=h.analyze;calls=[0]
    def interrupt(*a,**kw):
        calls[0]+=1
        if calls[0]==238:raise LeaseLost('synthetic process crash')
        return original(*a,**kw)
    monkeypatch.setattr(h,'analyze',interrupt)
    with pytest.raises(LeaseLost):e.batch.run(ctx,{})
    with e.database.engine.begin() as c:
        partial=ItemStore.read(c,e.tenant,tid)
        before=c.execute(select(acquisitions.c.request_count).filter_by(tenant_id=e.tenant,task_id=tid)).scalar_one()
        c.execute(update(work_items).filter_by(tenant_id=e.tenant,owner_id=tid).values(lease_expires=func.utc_timestamp(6)-__import__('sqlalchemy').text('INTERVAL 1 SECOND')))
    assert sum(r['analysisState']!='PENDING' for r in partial.values())==237
    monkeypatch.setattr(h,'analyze',original)
    assert Worker(e.service).once()
    report=e.service.read_report(e.principal,tid)
    assert report['dataReport']['summary']['processedCount']==1000
    with e.database.engine.connect() as c:after=c.execute(select(acquisitions.c.request_count).filter_by(tenant_id=e.tenant,task_id=tid)).scalar_one()
    assert after==before+1 # Only current source identity is rechecked; captured pages are integrity-verified and reused.


def test_one_bad_sku_does_not_discard_other_results(make_s01,tmp_path,monkeypatch):
    import commerce_hub.scenarios.s01_v2.handler as h
    e=environment(make_s01,tmp_path,20);original=h.analyze
    def fail(catalog,entity,*args,**kwargs):
        if entity['sku']=='V2-SKU-5':raise ValueError('synthetic malformed fields')
        return original(catalog,entity,*args,**kwargs)
    monkeypatch.setattr(h,'analyze',fail)
    _,report=run(e);s=report['dataReport']['summary']
    assert s['scopeObjectCount']==s['processedCount']==20 and s['failed']==1 and s['erpReference']==19


def single(e,tid):
    with e.database.engine.connect() as c:entity=next(r for r in ItemStore.read(c,e.tenant,tid).values() if r['productId']=='1')
    params=dict(entity={k:entity[k] for k in ['entityKey','sourceTenant','storeId','warehouseId','productId','sku','storeName','warehouseName']})
    view=e.service.create(e.principal,'single','S01_V2_SINGLE',e.scope,params,'synthetic')
    assert Worker(e.service).once()
    return view['taskRef']['taskId']


def test_single_explicitly_calls_gateway_and_preserves_unknown(make_s01,tmp_path):
    model=SyntheticModel();e=environment(make_s01,tmp_path,model=model);tid,_=run(e)
    assert model.calls==0
    sid=single(e,tid);report=e.service.read_report(e.principal,sid)
    assert model.calls==1 and report['analysisReport']['ai']['status']=='AVAILABLE', report['analysisReport']['ai']['reason']
    assert '未确认' in json.dumps(report['analysisReport']['ai']['explanation'],ensure_ascii=False)


def test_model_failure_preserves_persisted_deterministic_item(make_s01,tmp_path):
    class Failing(SyntheticModel):
        def invoke(self,request):raise TimeoutError('synthetic model timeout')
    e=environment(make_s01,tmp_path,model=Failing());tid,_=run(e)
    sid=single(e,tid);report=e.service.read_report(e.principal,sid)
    assert report['dataReport']['item']['quantity']==120
    assert report['analysisReport']['ai']['status']=='UNAVAILABLE'


def test_cancel_preserves_partial_results_and_explicit_retry_is_new_history(make_s01,tmp_path,monkeypatch):
    import commerce_hub.scenarios.s01_v2.handler as h
    e=environment(make_s01,tmp_path,1000);tid=e.create()['taskRef']['taskId']
    original=h.analyze;count=[0]
    def cancel(*args,**kwargs):
        item=original(*args,**kwargs);count[0]+=1
        if count[0]==30:
            view=e.service.read(e.principal,tid)
            e.service.cancel(e.principal,tid,'cancel',view['revision'],'synthetic')
        return item
    monkeypatch.setattr(h,'analyze',cancel)
    assert Worker(e.service).once()
    assert e.service.read(e.principal,tid)['state']=='CANCELLED'
    with e.database.engine.connect() as c:rows=ItemStore.read(c,e.tenant,tid)
    assert len(rows)==1000 and 0<sum(r['analysisState']!='PENDING' for r in rows.values())<1000
    monkeypatch.setattr(h,'analyze',original)
    retry=e.service.create(e.principal,'retry','S01_V2_BATCH',e.scope,{},'synthetic')['taskRef']['taskId']
    assert retry!=tid and Worker(e.service).once()
    assert e.service.read_report(e.principal,retry)['dataReport']['summary']['processedCount']==1000
    assert len(e.service.history(e.principal,e.scope,scenario_id='S01_V2_BATCH')['items'])==2


def test_reference_only_scheme_b_uses_p3_durable_create_submit_and_restart_replay(make_s01,tmp_path):
    e=environment(make_s01,tmp_path);tid,_=run(e);sid=single(e,tid)
    config=ERPConfig(access_token='synthetic-source-token')
    factory=lambda *_:TeachingRequisitionClient(config,transport=e.erp.transport,sleeper=lambda _:None)
    service=V2RequisitionService(e.service,e.policy,factory,tmp_path/'requisitions')
    result=service.confirm(e.principal,sid,'confirm',120,'','synthetic')
    assert result['state']=='SUBMITTED' and result['sourceGrade']=='REFERENCE_ONLY' and result['sourceAcknowledged']
    assert e.erp.mutations==2
    recovered=V2RequisitionService(e.service,e.policy,factory,tmp_path/'requisitions')
    assert recovered.confirm(e.principal,sid,'another-key',120,'','synthetic')==result and e.erp.mutations==2


def test_reference_only_lost_write_ack_reconciles_without_second_create(make_s01,tmp_path):
    e=environment(make_s01,tmp_path);tid,_=run(e);sid=single(e,tid);e.erp.lost_create=True
    factory=lambda *_:TeachingRequisitionClient(ERPConfig(access_token='synthetic-source-token'),transport=e.erp.transport,sleeper=lambda _:None)
    service=V2RequisitionService(e.service,e.policy,factory,tmp_path/'requisitions')
    result=service.confirm(e.principal,sid,'confirm',120,'','synthetic')
    assert result['state']=='SUBMITTED' and len(e.erp.orders)==1 and e.erp.mutations==2


def test_submit_revalidation_drift_stops_before_mutation(make_s01,tmp_path):
    e=environment(make_s01,tmp_path);tid,_=run(e);sid=single(e,tid)
    e.erp.data['quotes'][0]['unit_price']='3.00'
    factory=lambda *_:TeachingRequisitionClient(ERPConfig(access_token='synthetic-source-token'),transport=e.erp.transport,sleeper=lambda _:None)
    service=V2RequisitionService(e.service,e.policy,factory,tmp_path/'requisitions')
    result=service.confirm(e.principal,sid,'confirm',120,'','synthetic')
    assert result['state']=='BLOCKED' and result['errorCode']=='ANALYSIS_CHANGED_REANALYZE' and e.erp.mutations==0


def test_http_csrf_acknowledgement_and_write_permission_are_server_enforced(make_s01,tmp_path,mysql_settings):
    from fastapi.testclient import TestClient
    from pydantic import SecretStr
    from datetime import datetime,timezone
    import jwt
    from commerce_hub.entrypoints.http.app import create_app
    e=environment(make_s01,tmp_path);tid,_=run(e);sid=single(e,tid)
    factory=lambda *_:TeachingRequisitionClient(ERPConfig(access_token='synthetic-source-token'),transport=e.erp.transport,sleeper=lambda _:None)
    e.service.v2_requisitions=V2RequisitionService(e.service,e.policy,factory,tmp_path/'requisitions')
    settings=mysql_settings.model_copy(update=dict(environment='test',auth_issuer='fixture-issuer',auth_audience='fixture-audience',
        auth_signing_key=SecretStr('fixture-key-'+'x'*64),browser_origin='https://testserver'))
    stamp=int(datetime.now(timezone.utc).timestamp())
    token=jwt.encode(dict(iss='fixture-issuer',aud='fixture-audience',sub=e.principal.principal_id,tid=e.tenant,jti=e.principal.token_id,rev=1,
        exp=stamp+600,iat=stamp,nbf=stamp-1),'fixture-key-'+'x'*64,algorithm='HS256')
    with TestClient(create_app(settings,e.service.registry),base_url='https://testserver') as client:
        client.app.state.tasks=e.service
        path=f'/api/v1/s01/v2/singles/{sid}/requisition'
        assert client.post(path,json=dict(finalQuantity=120,sourceAcknowledged=True),headers={'Idempotency-Key':'confirm'}).status_code==401
        assert client.post('/api/v1/session',headers={'Authorization':'Bearer '+token}).status_code==200
        assert client.post(path,json=dict(finalQuantity=120,sourceAcknowledged=True),headers={'Idempotency-Key':'confirm'}).status_code==403
        headers={'Idempotency-Key':'confirm','X-CSRF-Token':client.cookies.get('commerce_csrf'),'Origin':'https://testserver'}
        assert client.post(path,json=dict(finalQuantity=120,sourceAcknowledged=False),headers=headers).status_code==422
        for bad in [dict(finalQuantity=True,sourceAcknowledged=True),dict(finalQuantity=120,sourceAcknowledged=True,supplierId=999),dict(finalQuantity=120.5,sourceAcknowledged=True)]:
            assert client.post(path,json=bad,headers=headers).status_code==422
        assert client.get('/api/v1/s01/options').json()['v2Enabled'] is True
        values=client.get(f'/api/v1/s01/v2/batches/{tid}/items',params=dict(q='V2-SKU-1',limit=1)).json()
        assert values['total']==1 and values['items'][0]['sku']=='V2-SKU-1'
        with e.database.engine.begin() as c:c.execute(__import__('sqlalchemy').delete(grants).filter_by(tenant_id=e.tenant,action='s01:requisition'))
        assert client.post(path,json=dict(finalQuantity=120,sourceAcknowledged=True),headers=headers).status_code==403
        assert e.erp.mutations==0
