"""Business entry and reliable source associations, with explicit synthetic ERP."""
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from tests.support.b_source import BSourceERP
from commerce_hub.adapters.erp import ERPConfig,TeachingERPReader
from commerce_hub.scenarios.after_sales.source import SourceReader
from commerce_hub.orchestration.service import TaskError
from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.governance.access.tables import b_resource_grants
from tests.integration.after_sales.test_workflows import env,run_job,read,mutate


def reader(tmp_path,erp=None):
    erp=erp or BSourceERP()
    return SourceReader(lambda:TeachingERPReader(ERPConfig(access_token='synthetic-source-token',interval=.1),transport=erp.transport,sleeper=lambda _:None),
        {'Synthetic Store':dict(storeId='1',sourceTenant='1')},tmp_path)


def test_review_automatically_links_product_without_inventing_order(tmp_path):
    r=reader(tmp_path);inbox=r.inbox('Synthetic Store','reviews',lambda:None)
    assert inbox['items'][0]['identity']['productId']=='1'
    assert inbox['items'][0]['orderId']=='UNKNOWN'
    e=r.voice_evidence('71','reviews','Synthetic Store',lambda:None,'test')
    assert e['identity']['category']=='APPAREL' and e['identity']['orderId']=='UNKNOWN'
    assert e['identity']['warehouseId']=='UNKNOWN' and e['customerText']=='尺寸偏小，请核对描述'
    assert e['facts'][0]['domain']=='feedback'
    assert r.voice_evidence('72','feedback','Synthetic Store',lambda:None,'test-feedback')['identity']['orderId']=='81'


def test_source_scope_missing_duplicate_and_multi_line_do_not_guess(tmp_path):
    erp=BSourceERP();r=reader(tmp_path,erp)
    erp.data['products'].append(erp.data['products'][0] | dict(id=999))
    assert r.inbox('Synthetic Store','reviews',lambda:None)['items'][0]['identity'] is None
    erp.data['products'].pop();erp.data['sales'][0]['item_list'].append(dict(sku='V2-SKU-1'))
    e=r.voice_evidence('72','feedback','Synthetic Store',lambda:None,'multiple')
    assert e['identity'] is None and len(e['identityCandidates'])==2
    erp.voices['reviews'][0]['store_id']=2
    with pytest.raises(TaskError,match='SOURCE_IDENTITY_MISMATCH'):r.inbox('Synthetic Store','reviews',lambda:None)
    with pytest.raises(TaskError,match='SOURCE_SCOPE_DENIED'):r.inbox('Other','reviews',lambda:None)


@pytest.mark.mysql
def test_source_open_dedup_first_association_ai_and_unknown_warehouse_risk(env,tmp_path):
    e=env;r=reader(tmp_path)
    e.domain.source_reader=r
    for spec in e.specs.values():spec.handler.source_reader=r
    data=dict(title='ERP评价',message='',region='CN',platform='TEACHING',language='zh',erpStoreName='Synthetic Store',erpVoiceId='71',erpVoiceKind='reviews')
    c=e.domain.create_case(e.actor,uuid4().hex,data)
    assert e.domain.create_case(e.actor,uuid4().hex,data)['id']==c['id']
    run_job(e,'CASE',c['id'],'evidence');case=read(e,'CASE',c['id'])
    assert case['body']['identity']['productId']=='1' and len(case['body']['messages'])==1
    run_job(e,'CASE',c['id'],'evidence');assert len(read(e,'CASE',c['id'])['body']['messages'])==1
    run_job(e,'CASE',c['id'],'advice');case=read(e,'CASE',c['id'])
    assert case['body']['advice'][-1]['feedbackAI']['analysis']['status']=='AVAILABLE'
    inv=e.domain.investigation(e.actor,uuid4().hex,dict(kind='CASE',id=c['id'],text='调查反馈',evidenceRefs=['voice-reviews-71']))
    with pytest.raises(TaskError,match='RISK_SOURCE_MISMATCH'):
        e.domain.risk(e.actor,uuid4().hex,dict(investigationId=inv['id'],reason='待调查',limitations='仓库未知',datasetId=None,
            identity=dict(sourceTenant='1',productId='1',sku='V2-SKU-0',storeId='1',warehouseMode='EXPLICIT_IDS',warehouseIds=['UNKNOWN'])))
    with TestClient(create_app(e.settings,e.specs)) as client:
        client.headers['Authorization']='Bearer '+e.token
        assert client.get('/api/b/v1/source-inbox',params=dict(store='Synthetic Store',kind='reviews')).status_code==200
        assert client.get('/api/b/v1/source-inbox',params=dict(store='Synthetic Store',kind='reviews',dateFrom='2026-13-01')).status_code==422
        with e.database.engine.begin() as conn:conn.execute(update(b_resource_grants).filter_by(tenant_id=e.actor.tenant_id,action='b:case:write').values(active=False))
        assert client.get('/api/b/v1/source-inbox',params=dict(store='Synthetic Store',kind='reviews')).status_code==403


@pytest.mark.mysql
def test_invalid_model_references_preserve_partial_case_and_model_usage(env,tmp_path):
    import json
    e=env;r=reader(tmp_path);e.domain.source_reader=r
    for spec in e.specs.values():spec.handler.source_reader=r
    original=e.provider.invoke
    def forged(request):
        result=original(request)
        if request.control.purpose=='b.experience.explain.v1':
            output=json.loads(result.content);output['facts']=['made-up-reference']
            result=result.model_copy(update=dict(content=json.dumps(output)))
        return result
    e.provider.invoke=forged
    c=e.domain.create_case(e.actor,uuid4().hex,dict(title='ERP评价',message='',region='CN',platform='TEACHING',language='zh',erpStoreName='Synthetic Store',erpVoiceId='71',erpVoiceKind='reviews'))
    run_job(e,'CASE',c['id'],'evidence');run_job(e,'CASE',c['id'],'advice')
    case=read(e,'CASE',c['id']);result=case['body']['advice'][-1]['feedbackAI']
    assert result['classifications']['status']=='AVAILABLE'
    assert result['analysis']['status']=='UNAVAILABLE' and result['analysis']['reason']=='INVALID_OUTPUT'
    assert result['analysis']['usage']['totalTokens']==150
    assert case['body']['evidence']['facts'] and case['body']['messages']
