"""Actual domain/API checks; ERP and models are explicitly synthetic here."""
from copy import deepcopy
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.governance.access.tables import b_resource_grants
from commerce_hub.orchestration.service import TaskError
from commerce_hub.scenarios.after_sales.policies import advice_block_reason
from tests.integration.after_sales.test_workflows import env,read,run_job,mutate
from tests.integration.after_sales.test_product_remediation import reader


@pytest.mark.parametrize('change,reason',[
    ({'messages':[]},'CUSTOMER_MESSAGE_REQUIRED'),
    ({'evidence':{'latestUnverified':True}},'EVIDENCE_UNVERIFIED'),
    ({'evidence':{'facts':[]}},'EVIDENCE_REQUIRED'),
    ({'identity':{'category':'UNKNOWN'}},'CATEGORY_UNSUPPORTED'),
    ({'businessDate':None},'BUSINESS_DATE_REQUIRED'),
    ({'region':'UNKNOWN'},'POLICY_SCOPE_INCOMPLETE'),
])
def test_specific_generation_block_reasons(change,reason):
    case=dict(messages=[dict(text='问题')],evidence=dict(facts=[{}]),identity=dict(category='APPAREL'),businessDate='2026-11-16T00:00:00Z',region='US',platform='Amazon',language='zh')
    assert advice_block_reason(case | change)==reason


def test_source_never_promotes_ticket_title_into_customer_conversation(tmp_path):
    from tests.support.b_source import BSourceERP
    erp=BSourceERP();r=reader(tmp_path,erp)
    erp.tickets[0]['created_time']='2026-11-16T12:00:00+08:00'
    erp.data['sales'][0]['country']='US'
    e=r.evidence('91','Synthetic Store',lambda:None,'ticket-body')
    assert not e.get('customerText') and e['region']=='US'
    assert e['businessDate']=='2026-11-16T04:00:00+00:00'
    erp.tickets[0]['created_time']='2026-11-16 12:00:00'
    assert r.evidence('91','Synthetic Store',lambda:None,'ticket-naive')['businessDate'] is None


@pytest.mark.mysql
def test_no_customer_message_is_not_a_successful_ai_reply(env):
    e=env;r=reader(__import__('pathlib').Path('.tmp/b-usability-source'));e.domain.source_reader=r
    for spec in e.specs.values():spec.handler.source_reader=r
    c=e.domain.create_case(e.actor,uuid4().hex,dict(title='标题',message='',region='US',platform='Amazon',language='zh',erpStoreName='Synthetic Store',erpTicketId='91'))
    run_job(e,'CASE',c['id'],'evidence');run_job(e,'CASE',c['id'],'advice')
    ai=read(e,'CASE',c['id'])['body']['advice'][-1]['ai']
    assert ai==dict(status='NOT_ATTEMPTED',reason='CUSTOMER_MESSAGE_REQUIRED',output=None)
    assert not e.provider.calls


@pytest.mark.mysql
def test_workspace_management_capabilities_follow_server_grants(env):
    e=env
    with TestClient(create_app(e.settings,e.specs)) as client:
        client.headers['Authorization']='Bearer '+e.token
        assert all(client.get('/api/b/v1/workspace').json()['capabilities'].values())
        with e.database.engine.begin() as conn:
            conn.execute(update(b_resource_grants).filter_by(tenant_id=e.actor.tenant_id).where(b_resource_grants.c.action.in_(['b:policy:write','b:policy:publish','b:dataset:manage','b:binding:manage'])).values(active=False))
        caps=client.get('/api/b/v1/workspace').json()['capabilities']
        assert not any(caps.values())
        from commerce_hub.scenarios.after_sales.policy_templates import policy_starters
        assert client.post('/api/b/v1/policies',headers={'Idempotency-Key':uuid4().hex},json={k:v for k,v in policy_starters()[0].items() if k!='id'}).status_code==403


@pytest.mark.mysql
def test_supplemental_conversation_is_audited_deduped_and_cannot_change_erp_facts(env,tmp_path):
    import json
    from tests.support.b_source import BSourceERP
    from commerce_hub.scenarios.after_sales.customer_context import NATURE
    e=env;erp=BSourceERP();r=reader(tmp_path,erp);e.domain.source_reader=r
    for spec in e.specs.values():spec.handler.source_reader=r
    manifest=dict(schemaVersion='1.0.0',datasetId='test-owned-batch',version='v1',sourceNature=NATURE,items=[dict(
        erpTicketId='91',erpStoreName='Synthetic Store',sourceTenant='1',storeId='1',orderId='81',orderNumber='SYN-ORDER',productId='1',sku='V2-SKU-0',
        provenance='SUPPLEMENTAL_SIMULATED_CUSTOMER_STATEMENT',text='袖口接缝松了，还没有寄回。',at='2026-11-16T12:00:00+08:00')])
    r.supplemental_context=tmp_path/'claims.json';r.supplemental_context.write_text(json.dumps(manifest),encoding='utf-8')
    c=e.domain.create_case(e.actor,uuid4().hex,dict(title='标题',message='',region='US',platform='Amazon',language='zh',erpStoreName='Synthetic Store',erpTicketId='91'))
    run_job(e,'CASE',c['id'],'evidence');run_job(e,'CASE',c['id'],'evidence')
    case=read(e,'CASE',c['id']);assert len(case['body']['messages'])==1
    msg=case['body']['messages'][0];assert msg['source']=='SIMULATED' and msg['sourceNature']==NATURE and msg['manifestHash']
    assert not any(f['domain']=='return' for f in case['body']['evidence']['facts'])
    erp.data['products'][0]['name']='Current natural product name'
    run_job(e,'CASE',c['id'],'evidence');assert read(e,'CASE',c['id'])['body']['identity']['name']=='Current natural product name'
    # A copied claim cannot bind a different ERP order or source identity.
    manifest['items'][0]['orderId']='other';r.supplemental_context.write_text(json.dumps(manifest),encoding='utf-8')
    with pytest.raises(TaskError,match='CUSTOMER_CONTEXT_RELATION_MISMATCH'):r.evidence('91','Synthetic Store',lambda:None,'cross-order')
