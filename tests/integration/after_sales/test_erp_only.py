"""Removed independent-data capability cannot be used through old URLs or jobs."""
from copy import deepcopy
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, func
from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.scenarios.after_sales.common import scope, WORKSPACE, digest, now, timestamp
from commerce_hub.scenarios.after_sales.tables import assets, versions
from commerce_hub.scenarios.after_sales.handler import Handler
from commerce_hub.scenarios.after_sales.risk import QualityRiskReadPort
from commerce_hub.scenarios.after_sales.s01_advisory import attach
from commerce_hub.orchestration.service import TaskError
from tests.integration.after_sales.test_workflows import env, read, mutate, run_job, publish_policies
from tests.integration.after_sales.test_owned_scope import owned


def legacy(e, kind, body, state='ACTIVE'):
    """Seed an existing historical row, never through a removed product command."""
    rid=uuid4().hex;resource=scope(e.actor.tenant_id,'CASE');resource.update(resourceId=rid,createParent=False)
    with e.database.engine.begin() as conn:
        conn.execute(insert(assets).values(tenant_id=e.actor.tenant_id,kind=kind,id=rid,workspace=WORKSPACE,scope=resource,
            revision=1,state=state,body=body,created_by=e.actor.principal_id,created_at=func.utc_timestamp(6),updated_at=func.utc_timestamp(6)))
        conn.execute(insert(versions).values(tenant_id=e.actor.tenant_id,kind=kind,id=rid,version=1,body=body,
            content_hash=digest(body),actor=e.actor.principal_id,created_at=func.utc_timestamp(6)))
    return rid


@pytest.mark.mysql
def test_removed_collections_import_mapping_and_tasks_are_unavailable(env):
    e=env
    assert set(e.specs)=={'B_CASE_EVIDENCE_V1','B_CASE_ADVICE_V1','B_INVESTIGATION_ASSIST_V1'}
    for job in ['validate','analysis','binding']:
        with pytest.raises(TaskError,match='ACTION_INVALID'):Handler(job)
        with pytest.raises(TaskError,match='ACTION_INVALID'):
            e.domain.job(e.actor,'DATASET','old',job,uuid4().hex,1,{})
    for method in ['create_dataset','upload','records']:assert not hasattr(e.domain,method)
    with TestClient(create_app(e.settings,e.specs)) as client:
        client.headers['Authorization']='Bearer '+e.token
        for path in ['teaching-package','mapping-options?datasetId=old&store=x&sku=y','datasets','datasets/old','datasets/old/records','analyses','analyses/old','teaching-bindings','teaching-bindings/old']:
            assert client.get('/api/b/v1/'+path).status_code in {404,405},path
        for path,payload in [('datasets',{'manifest':{}}),('datasets/old/chunks',{'expectedRevision':1,'number':0,'records':[]}),
                             ('datasets/old/validation-jobs',{'expectedRevision':1}),('datasets/old/analysis-jobs',{'expectedRevision':1}),
                             ('datasets/old/binding-jobs',{'expectedRevision':1}),('teaching-bindings/old/revoke',{'expectedRevision':1})]:
            assert client.post('/api/b/v1/'+path,json=payload,headers={'Idempotency-Key':uuid4().hex}).status_code in {404,405,422},path
        assert client.post('/api/b/v1/datasets/old/chunks',json={'expectedRevision':1},headers={'Idempotency-Key':uuid4().hex}).status_code==404
        data=dict(title='本地资料案件',message='尺码不合适',region='CN',platform='TEACHING',language='zh')
        assert client.post('/api/b/v1/cases',json=data,headers={'Idempotency-Key':uuid4().hex}).status_code==422
        assert client.post('/api/b/v1/cases',json=data|{'datasetId':'old'},headers={'Idempotency-Key':uuid4().hex}).status_code==422
        assert client.get('/api/b/v1/workspace').json()['capabilities']=={'policyWrite':True,'policyPublish':True}
        assert set(client.get('/api/b/v1/workbench').json())=={'case','policy','investigation','risk'}
        starters=client.get('/api/b/v1/policy-starters',params={'region':'US','platform':'Amazon'}).json()
        assert len(starters)==12 and all(p['region']=='US' and p['platform']=='Amazon' and '教学' in p['source'] for p in starters)
        assert {'LOGISTICS','NOT_RECEIVED','ORDER_CHANGE','PRODUCT_INFO','ITEM_ISSUE','PAYMENT'}<={topic for p in starters for topic in p['topics']}


@pytest.mark.mysql
def test_historical_independent_assets_are_retained_but_never_business_visible(env):
    e=env
    ids={kind:legacy(e,kind,dict(origin={'kind':'CASE','id':'old'},identity={},investigationId='old')) for kind in ['CASE','DATASET','REPORT','INVESTIGATION','RISK','BINDING']}
    with TestClient(create_app(e.settings,e.specs)) as client:
        client.headers['Authorization']='Bearer '+e.token
        for kind,rid in ids.items():
            assert e.domain.store.list(e.actor,kind)['items']==[]
            with pytest.raises(TaskError,match='NOT_FOUND'):read(e,kind,rid)
        assert client.get('/api/b/v1/cases/'+ids['CASE']).status_code==404
        assert client.get('/api/b/v1/cases/'+ids['CASE']+'?version=1').status_code==404
        assert client.get('/api/b/v1/risks/'+ids['RISK']).status_code==404
        assert client.post('/api/b/v1/cases/'+ids['CASE']+'/evidence-jobs',json={'expectedRevision':1},headers={'Idempotency-Key':uuid4().hex}).status_code==404
    publish_policies(e)
    from commerce_hub.scenarios.after_sales.policy_templates import policy_starters
    assert {p['body']['title'] for p in e.domain.store.list(e.actor,'POLICY')['items']}=={p['title'] for p in policy_starters()}
    with e.database.engine.connect() as conn:
        for kind,rid in ids.items():
            assert conn.execute(select(assets.c.revision).filter_by(tenant_id=e.actor.tenant_id,kind=kind,id=rid)).scalar_one()==1
            assert conn.execute(select(versions.c.version).filter_by(tenant_id=e.actor.tenant_id,kind=kind,id=rid)).scalar_one()==1


@pytest.mark.mysql
def test_erp_investigation_confirm_revoke_expiry_and_advisory_preserve_business_fields(env,tmp_path):
    import json
    from types import SimpleNamespace as NS
    from urllib.parse import urlsplit
    from tests.support.b_source import BSourceERP
    erp=BSourceERP();erp.data['sales'][0].update(shipping_warehouse='Synthetic Warehouse',item_list=[dict(sku='V2-SKU-0',quantity=2)])
    original=erp.transport
    def transport(method,target,headers,body,config):
        path=urlsplit(target).path
        if path.startswith('/api/v1/sales-workflow/'):
            return 200,json.dumps(dict(data=dict(local_only=True,order_id=81,state='shipped',shipments=[dict(order_id=81,outbound_id=7)]))).encode()
        if path=='/api/v1/stock/ledger':
            row=dict(id=8,resource='outbound-orders',record_id=7,inventory_id=10001,sku='V2-SKU-0',warehouse_name='Synthetic Warehouse',operation='post',reverses_id=None,delta_quantity=-2,delta_available=-2,before_quantity=10,after_quantity=8,before_available=10,after_available=8)
            return 200,json.dumps(dict(items=[row],total=1)).encode()
        return original(method,target,headers,body,config)
    erp.transport=transport
    e=env;r=owned(tmp_path,erp)
    r.owned_provider=lambda:[NS(storeName='Synthetic Store',sourceTenant='1',sourceStore='1',sourceWarehouse='1',warehouseName='Synthetic Warehouse',sku='V2-SKU-0',monitor=NS(productId='1',salesIds=('81',),inventoryIds=('10001',)))]
    e.domain.source_reader=r
    for spec in e.specs.values():spec.handler.source_reader=r
    c=e.domain.create_case(e.actor,uuid4().hex,dict(title='尺码需核实',message='吊牌保留，尺码不合适',region='CN',platform='TEACHING',language='zh',businessDate='2026-09-05T00:00:00Z',erpStoreName='Synthetic Store',erpTicketId='91'))
    run_job(e,'CASE',c['id'],'evidence');case=read(e,'CASE',c['id']);linked=case['body']['identity'];assert linked['warehouseId']=='1'
    refs=[case['body']['evidence']['facts'][0]['id']]
    inv=e.domain.investigation(e.actor,uuid4().hex,dict(kind='CASE',id=c['id'],text='核实尺码',evidenceRefs=refs))
    identity=dict(sourceTenant='1',productId='1',sku='V2-SKU-0',storeId='1',warehouseMode='EXPLICIT_IDS',warehouseIds=['1'])
    risk=e.domain.risk(e.actor,uuid4().hex,dict(investigationId=inv['id'],reason='尺码描述需跟进',limitations='待扩大样本核查',identity=identity))
    item=dict(sourceTenant='1',productId='1',sku='V2-SKU-0',storeId='1',warehouseId='1',quantity=100,inventory={'available':10},procurementEligibility={'eligible':True},candidates=[100])
    port=QualityRiskReadPort(e.domain)
    assert not port.lookup(e.actor,[item])[0]['riskRefs']
    with pytest.raises(TaskError,match='INVESTIGATION_CONCLUSION_REQUIRED'):
        mutate(e,'RISK',risk['id'],'decisions',dict(decision='CONFIRM',reason='尚无结论',validUntil=None))
    mutate(e,'INVESTIGATION',inv['id'],'entries',dict(text='已核对支持继续跟进',evidenceRefs=refs,conclusion='SUPPORTED'))
    mutate(e,'RISK',risk['id'],'decisions',dict(decision='CONFIRM',reason='人工确认',validUntil=None))
    shown=attach(e.domain,e.actor,[item])[0];saved=port.lookup(e.actor,[item])
    assert shown['qualityRiskAdvisory']['status']=='MATCHED'
    assert {k:v for k,v in shown.items() if k!='qualityRiskAdvisory'}==item
    for field in ['sourceTenant','productId','sku','storeId','warehouseId']:
        assert not port.lookup(e.actor,[item|{field:'wrong'}])[0]['riskRefs']
    assert not port.lookup(e.actor,[item],as_of=read(e,'RISK',risk['id'])['body']['validUntil'])[0]['riskRefs']
    mutate(e,'RISK',risk['id'],'decisions',dict(decision='REVOKE',reason='跟进结束',validUntil=None))
    assert not port.lookup(e.actor,[item])[0]['riskRefs']
    assert port.historical(e.actor,saved)[0]['riskRefs'][0]['version']==2
    r.owned_provider=lambda:[]
    assert port.historical(e.actor,saved)[0]['riskRefs']==[]
