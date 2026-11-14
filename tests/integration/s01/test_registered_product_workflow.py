"""Owned product path over real isolated MySQL/API/Worker and synthetic ERP only."""
from datetime import datetime,timezone
from decimal import Decimal
import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from commerce_hub.adapters.erp import ERPConfig
from commerce_hub.adapters.erp_requisition import TeachingRequisitionClient
from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.orchestration.worker import Worker
from commerce_hub.scenarios.s01_v2.requisition import V2RequisitionService
from tests.integration.orchestration.test_s01_reports import make_s01
from tests.integration.s01.test_v2_workflow import environment,run,single,SyntheticModel
from tests.support.admission_runtime import AdmissionERP

pytestmark=pytest.mark.mysql


def owned_environment(make_s01,tmp_path,model=None):
    e=environment(make_s01,tmp_path,0,model=model)
    e.erp=AdmissionERP()
    e.policy.owned_only=True;e.policy.owned_mappings=[e.erp.mapping]
    return e


def test_owned_worker_captures_exact_members_and_retains_reference_after_new_day(make_s01,tmp_path):
    e=owned_environment(make_s01,tmp_path);tid,report=run(e)
    d=report['dataReport'];s=d['summary']
    assert d['analysisRange']=='OWNED_REGISTERED' and len(d['monitoring']['members'])==1
    assert s['discoveredSkuCount']==s['scopeObjectCount']==s['replenishSkuCount']==1
    sid=single(e,tid);item=e.service.read_report(e.principal,sid)['dataReport']['item']
    assert item['decision']['referenceReplenishmentQuantity']==45 and item['quantity']==48
    assert item['registeredMembership']['datasetId']==e.erp.mapping.monitor.datasetId
    assert item['decision']['forecast']['orderCount']==7 and e.erp.mutations==0
    assert all('ids' in p and 'date_from' not in p for _,path,p in e.erp.calls if path=='/api/v1/sales-orders')


def test_owned_business_ai_is_explicit_and_keeps_reference_numbers(make_s01,tmp_path):
    model=SyntheticModel();e=owned_environment(make_s01,tmp_path,model=model);tid,_=run(e)
    sid=single(e,tid);report=e.service.read_report(e.principal,sid)
    assert report['analysisReport']['ai']['status']=='AVAILABLE' and model.calls==1
    assert report['dataReport']['item']['decision']['referenceReplenishmentQuantity']==45
    assert any('39' in f['text'] for f in report['analysisReport']['ai']['explanation']['keyEvidence'])
    original=e.service.read(e.principal,sid)['parameters'] if 'parameters' in e.service.read(e.principal,sid) else None
    entity={k:report['dataReport']['item'][k] for k in ['entityKey','sourceTenant','storeId','warehouseId','productId','sku','storeName','warehouseName']}
    view=e.service.create(e.principal,'no-ai-with-provider','S01_V2_SINGLE',e.scope,dict(entity=entity,explainAI=False),'synthetic')
    assert Worker(e.service).once()
    assert e.service.read_report(e.principal,view['taskRef']['taskId'])['analysisReport']['ai']['status']=='NOT_ATTEMPTED'
    assert model.calls==1 and e.erp.mutations==0


@pytest.mark.parametrize('drift',[False,True])
def test_owned_procurement_revalidates_same_membership_and_safe_mock_submission(make_s01,tmp_path,drift):
    e=owned_environment(make_s01,tmp_path);tid,_=run(e);sid=single(e,tid)
    if drift:e.erp.data['quotes'][0]['unit_price']='3.00'
    factory=lambda *_:TeachingRequisitionClient(ERPConfig(access_token='synthetic-source-token'),transport=e.erp.transport,sleeper=lambda _:None)
    service=V2RequisitionService(e.service,e.policy,factory,tmp_path/'requisitions')
    result=service.confirm(e.principal,sid,'owned-confirm',48,'','synthetic')
    if drift:
        assert result['state']=='BLOCKED' and result['errorCode']=='ANALYSIS_CHANGED_REANALYZE' and e.erp.mutations==0
    else:
        assert result['state']=='SUBMITTED' and result['sourceGrade']=='PLATFORM_REFERENCE' and e.erp.mutations==2
        assert service.confirm(e.principal,sid,'replay',48,'','synthetic')==result and e.erp.mutations==2


def test_owned_api_group_filters_default_no_ai_and_rejects_removed_member(make_s01,tmp_path,mysql_settings):
    e=owned_environment(make_s01,tmp_path);tid,_=run(e)
    key='fixture-key-'+'x'*64
    settings=mysql_settings.model_copy(update=dict(environment='test',auth_issuer='fixture-issuer',auth_audience='fixture-audience',
        auth_signing_key=SecretStr(key),browser_origin='https://testserver'))
    stamp=int(datetime.now(timezone.utc).timestamp())
    token=jwt.encode(dict(iss='fixture-issuer',aud='fixture-audience',sub=e.principal.principal_id,tid=e.tenant,jti=e.principal.token_id,rev=1,
        exp=stamp+600,iat=stamp,nbf=stamp-1),key,algorithm='HS256')
    with TestClient(create_app(settings,e.service.registry),base_url='https://testserver') as client:
        client.app.state.tasks=e.service
        assert client.post('/api/v1/session',headers={'Authorization':'Bearer '+token}).status_code==200
        headers={'Idempotency-Key':'owned-single','X-CSRF-Token':client.cookies.get('commerce_csrf'),'Origin':'https://testserver'}
        root='/api/v1/s01/v2'
        assert client.get(root+'/options').json()['analysisRange']=='OWNED_REGISTERED'
        progress=client.get(root+'/batches/'+tid).json()
        assert progress['analysisRange']=='OWNED_REGISTERED' and progress['summary']['replenishSkuCount']==1
        listing=client.get(root+'/batches/'+tid+'/items',params=dict(group='sku',decision='REPLENISH')).json()
        assert listing['total']==1 and listing['items'][0]['productSummary']['scopeCount']==1
        assert client.get(root+'/batches/'+tid+'/items',params=dict(group='sku',decision='NO_REPLENISHMENT')).json()['total']==0
        entity=listing['items'][0]['entityKey']
        detail=client.get(root+'/batches/'+tid+'/items/'+entity).json()
        assert len(detail['relatedScopes'])==1
        body=dict(batchId=tid,entityKey=entity)
        response=client.post(root+'/singles',json=body,headers=headers)
        assert response.status_code==202 and Worker(e.service).once()
        sid=response.json()['taskRef']['taskId']
        assert client.get(root+'/singles/'+sid).json()['report']['analysisReport']['ai']['status']=='NOT_ATTEMPTED'
        e.policy.owned_mappings=[];headers['Idempotency-Key']='removed-member'
        assert client.post(root+'/singles',json=body,headers=headers).status_code==403
        assert e.erp.mutations==0
