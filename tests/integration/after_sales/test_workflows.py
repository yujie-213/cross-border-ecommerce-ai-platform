"""Real isolated MySQL/O01/G01; synthetic business fixtures and model transport.

These are engineering end-to-end tests, never evidence of a paid model call or
real ERP return population. The actual product uses the same handlers and APIs.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import json
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import SecretStr
from sqlalchemy import select,update
from fastapi.testclient import TestClient

from commerce_hub.bootstrap.after_sales import registry
from commerce_hub.bootstrap.composition import task_service
from commerce_hub.capabilities.models.contracts import ProviderResult,Usage
from commerce_hub.capabilities.metrics.after_sales import analyze,validate_records,DEFAULT_RULE
from commerce_hub.entrypoints.enable_after_sales import configuration,account_fingerprint
from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.governance.access.b_admin import grant_after_sales
from commerce_hub.governance.access.local import LocalAdmin
from commerce_hub.governance.access.service import AccessControl,AccessDenied
from commerce_hub.governance.observability.service import Audit
from commerce_hub.orchestration.contracts import DomainResult
from commerce_hub.orchestration.service import TaskError,HandlerSpec
from commerce_hub.orchestration.worker import Worker
from commerce_hub.scenarios.after_sales.common import SOURCE,now,timestamp,digest,scope
from tests.support.b_metrics_fixture import golden_package
from commerce_hub.scenarios.after_sales.policy_templates import policy_starters
from commerce_hub.scenarios.after_sales.tables import assets,steps,manifests
from commerce_hub.scenarios.after_sales.risk import QualityRiskReadPort
from commerce_hub.scenarios.after_sales.s01_advisory import attach
from commerce_hub.scenarios.after_sales.policies import applicable,validate_advice


class SyntheticProvider:
    """Test transport only; derives outputs from the supplied model context."""
    def __init__(self):self.calls=[]
    def describe_capabilities(self):return {'structured_output'}
    def preflight(self,payload,cost):pass
    def invoke(self,request):
        assert request.control.snapshotId and request.control.snapshotId != 'b-input'
        self.calls.append(request.control.logicalCallId)
        data=json.loads(request.payload.messages[1].content)
        if request.control.purpose=='b.case.advice.v1':
            output=dict(replyDraft='感谢您的反馈，收到后我们会协助核实，并根据核实结果告知可选处理方式。',adviceCode='MANUAL_REVIEW',
                citations=([{k:data['policies'][0][k] for k in ('policyId','version','sectionId','hash')}] if data['policies'] else []),
                missingEvidence=['请提供问题照片'],escalation=False)
        elif request.control.purpose=='b.feedback.classify.v1':
            output=dict(items=[dict(feedbackId=f['feedbackId'],labels=['SIZE' if '尺寸' in f['text'] else 'COMPATIBILITY'],span=f['text']) for f in data['feedback']])
        else:output=dict(facts=data['factRefs'],hypotheses=['需调查尺寸描述与客户预期是否一致'],alternativeExplanations=['也可能存在客户选码差异'],missingEvidence=['需核对商品尺码表'],nextSteps=['人工抽查反馈和商品描述'])
        return ProviderResult(status='COMPLETED',content=json.dumps(output,ensure_ascii=False),finishReason='stop',actualModelRevision='deepseek-flash',
            usage=Usage(inputTokens=100,outputTokens=50,totalTokens=150,actualCost=Decimal('.00100000'),currency='USD',pricingVersion='synthetic-v1'))




@pytest.fixture
def env(database,mysql_settings):
    tenant='b-workflow-'+uuid4().hex
    key='synthetic-only-'+('x'*64)
    access=AccessControl(database.engine,'b-test','b-test',key)
    legacy_scope=dict(tenantId=tenant,storeIds=['store'],warehouseIds=['warehouse'],canonicalSkuIds=['sku'],fields=['quantity'])
    admin=LocalAdmin(access,tenant,legacy_scope);admin.initialize('synthetic-only-password')
    token,_=admin.login('admin','synthetic-only-password');actor=access.authenticate(token)
    grant_after_sales(database.engine,Audit(),installation_id='test-only',tenant_id=tenant,configuration=configuration(tenant),dry_run=False)
    settings=mysql_settings.model_copy(update=dict(environment='test',after_sales_enabled=True,auth_issuer='b-test',auth_audience='b-test',auth_signing_key=SecretStr(key),browser_origin='https://testserver'))
    specs=registry(settings);provider=SyntheticProvider()
    for scenario,spec in list(specs.items()):
        spec=replace(spec,work_kind='b-test.'+tenant+'.'+spec.handler.job);specs[scenario]=spec
        from tests.integration.after_sales.test_product_remediation import reader
        from pathlib import Path
        spec.handler.source_reader=reader(Path('.tmp/b-source')/tenant)
        if spec.handler.job in {'analysis','advice','investigation'}:
            spec.handler.provider=provider
            specs[scenario]=replace(spec,max_calls=10,max_tokens=240000,max_cost=Decimal('.5'),cost_currency='USD',policy_version='b-synthetic-model-test')
    tasks=task_service(database,settings,specs)
    return SimpleNamespace(tasks=tasks,domain=tasks.after_sales,actor=actor,token=token,settings=settings,specs=specs,provider=provider,database=database)


def read(e,kind,rid):return e.domain.store.read(e.actor,kind,rid)


def mutate(e,kind,rid,action,data=None,revision=None):
    row=read(e,kind,rid)
    return e.domain.mutate(e.actor,kind,rid,action,uuid4().hex,revision or row['revision'],data or {})


def run_job(e,kind,rid,job,data=None):
    row=read(e,kind,rid)
    accepted=e.domain.job(e.actor,kind,rid,job,uuid4().hex,row['revision'],data or {})
    worker=Worker(e.tasks);stop=time.monotonic()+2
    while not worker.once():
        assert time.monotonic()<stop,'No delivery became claimable within two seconds'
        time.sleep(.02)
    task=e.tasks.read(e.actor,accepted['taskRef']['taskId'])
    assert task['state']=='SUCCEEDED',task
    return e.tasks.read_report(e.actor,task['taskRef']['taskId'])






def publish_policies(e):
    for p in policy_starters():
        data={k:v for k,v in p.items() if k!='id'}
        result=e.domain.create_policy(e.actor,uuid4().hex,data)
        mutate(e,'POLICY',result['id'],'submit-review')
        mutate(e,'POLICY',result['id'],'publish',dict(reason='synthetic human publication fixture'))








@pytest.mark.mysql
def test_http_real_identity_commands_csrf_ownership_and_restart(env):
    e=env
    with TestClient(create_app(e.settings,e.specs)) as client:
        client.headers['Authorization']='Bearer '+e.token
        assert client.get('/api/b/v1/status').status_code==200
        assert client.get('/api/b/v1/workspace').status_code==200
        data=dict(title='ERP工单',message='需要人工协助',region='CN',platform='TEACHING',language='zh',erpStoreName='Synthetic Store',erpTicketId='91')
        key=uuid4().hex
        result=client.post('/api/b/v1/cases',json=data,headers={'Idempotency-Key':key})
        assert result.status_code==200,result.text
        rid=result.json()['id']
        assert client.post('/api/b/v1/cases',json=data,headers={'Idempotency-Key':key}).json()==result.json()
        assert client.post('/api/b/v1/cases',json=data|{'message':'不同内容'},headers={'Idempotency-Key':key}).status_code==409
        assert client.get('/api/b/v1/cases/'+rid).json()['body']['identity'] is None
        assert client.post('/api/b/v1/cases',json=data|{'actor':'admin'},headers={'Idempotency-Key':uuid4().hex}).status_code==422
        assert client.post('/api/b/v1/risk-lookups',json={'identities':[],'mode':'TEACHING'}).status_code==422
        # Revoked principal resource access hides the object and the count.
        from commerce_hub.governance.access.tables import b_resource_grants
        with e.database.engine.begin() as conn:conn.execute(update(b_resource_grants).filter_by(tenant_id=e.actor.tenant_id,action='b:read').values(active=False))
        assert client.get('/api/b/v1/cases/'+rid).status_code==404
        assert client.get('/api/b/v1/cases').json()['items']==[]


def golden():
    m,b=golden_package();return m,sum(b,[])


def rehash(m,records):
    from collections import Counter
    m['counts']=dict(Counter(r['type'] for r in records));return m


def test_ac02_exact_ratios_repeat_and_versioned_rules():
    m,r=golden();a=analyze(r,m,m['windows'],m['asOf']);assert a==analyze(r,m,m['windows'],m['asOf'])
    assert a['items'][0]['groups'][1]['numerator']==12
    assert a['items'][0]['groups'][1]['stages']['refunded']==12
    assert a['items'][0]['groups'][1]['denominator']==40
    rule=DEFAULT_RULE|dict(version='high-threshold-test',deltaBasisPoints=3000)
    assert analyze(r,m,m['windows'],m['asOf'],rule)['items'][0]['finding']=='NO_THRESHOLD_SIGNAL'
    assert a['items'][0]['finding']=='NEEDS_INVESTIGATION'


@pytest.mark.parametrize('defect,code',[
    ('mixed','SOURCE_MIXED'),('coverage','COVERAGE_INCOMPLETE'),('timezone','TIMEZONE_UNKNOWN'),('conflict','DUPLICATE_CONFLICT'),
    ('quantity','RETURN_EXCEEDS_SHIPMENT'),('population','POPULATION_INCOMPLETE'),('stage','RETURN_CAUSAL_CONFLICT'),('wrong-sku','IDENTITY_UNRESOLVED')])
def test_ac02_rejects_corrupt_fixed_population(defect,code):
    m,r=golden()
    if defect=='mixed':r[-1]['sourceNature']='TEACHING_ERP_OBSERVED'
    if defect=='coverage':m['coverageComplete']=False
    if defect=='timezone':m['timezone']='UNKNOWN'
    if defect=='conflict':r.append(deepcopy(next(x for x in r if x['type']=='shipment')));r[-1]['quantity']=1
    if defect=='quantity':next(x for x in r if x['type']=='return')['quantity']=999
    if defect=='population':m['population'].pop()
    if defect=='stage':next(x for x in r if x['type']=='return')['stage']='refunded'
    if defect=='wrong-sku':next(x for x in r if x['type']=='line')['sku']='wrong'
    with pytest.raises(TaskError,match=code):validate_records(r,m)


def test_ac02_maturity_partial_fulfillment_zero_denominator_and_sample_unknown():
    m,r=golden();result=analyze(r,m,m['windows'],'2026-09-30T00:00:00Z')
    assert all(i['groups'][1]['ratePercent'] is None and i['finding']=='UNKNOWN' for i in result['items'])
    next(x for x in r if x['type']=='line')['fulfillmentComplete']=False
    assert analyze(r,m,m['windows'],m['asOf'])['items'][0]['groups'][0]['status']=='UNKNOWN'
    m,r=golden();r=[x for x in r if x['type']!='shipment' and x['type']!='return'];rehash(m,r)
    for line in r:
        if line['type']=='line':line['fulfillmentComplete']=False
    result=analyze(r,m,m['windows'],m['asOf'])
    assert all(g['ratePercent'] is None for i in result['items'] for g in i['groups'])


def test_ac01_policy_filters_forged_refs_and_unsupported_promises():
    from commerce_hub.scenarios.after_sales.policies import retrieve
    policy=dict(id='p',revision=3,state='PUBLISHED',body={k:v for k,v in policy_starters()[0].items() if k!='id'})
    case=dict(identity={'category':'APPAREL'},region='CN',platform='TEACHING',language='zh',messages=[dict(text='尺码')])
    refs=retrieve([policy],case,'2026-09-01T00:00:00Z');assert refs
    for state in ['DRAFT','IN_REVIEW','REVOKED']:assert not retrieve([policy|dict(state=state)],case,'2026-09-01T00:00:00Z')
    for date in ['2025-01-01T00:00:00Z','2027-01-01T00:00:00Z',None]:assert not retrieve([policy],case,date)
    for key in ['region','platform','language']:assert not retrieve([policy],case|{key:'WRONG'},'2026-09-01T00:00:00Z')
    output=dict(replyDraft='请提供问题照片供人工核实',adviceCode='MANUAL_REVIEW',citations=[{k:refs[0][k] for k in ('policyId','version','sectionId','hash')}],missingEvidence=[],escalation=False)
    assert validate_advice(output,refs)
    for bad in ['保证退款','三天内到账','退款100元','请拆机检查']:
        with pytest.raises(TaskError):validate_advice(output|dict(replyDraft=bad),refs)
    output['citations'][0]['hash']='forged'
    with pytest.raises(TaskError,match='CITATION_FORGED'):validate_advice(output,refs)


def test_contract_legacy_read_and_teaching_version_pairing():
    legacy=dict(contractVersion='0.1.0',sourceNature='SIMULATED_ENGINEERING',completeness='RULES_ONLY',scope={},snapshotRef='x',dataReport={},analysisReport={})
    assert DomainResult.model_validate(legacy).sourceBundleRef is None
    with pytest.raises(ValueError):DomainResult.model_validate(legacy|dict(sourceNature=SOURCE))
    assert DomainResult.model_validate(legacy|dict(contractVersion='0.2.0',sourceNature=SOURCE,sourceBundleRef={'id':'manifest'}))


def erp_case(e,text='衣服尺寸偏小，与描述不一致。'):
    c=e.domain.create_case(e.actor,uuid4().hex,dict(title='尺码问题',message=text,region='CN',platform='TEACHING',language='zh',businessDate='2026-09-05T00:00:00Z',erpStoreName='Synthetic Store',erpTicketId='91'))
    run_job(e,'CASE',c['id'],'evidence')
    return read(e,'CASE',c['id'])


@pytest.mark.mysql
def test_erp_case_policy_ai_human_reply_history_stale_and_safety(env):
    e=env;publish_policies(e);original=account_fingerprint(e.database,e.actor.tenant_id)
    c=erp_case(e);assert c['body']['identity']['orderId']=='81'
    run_job(e,'CASE',c['id'],'advice');c=read(e,'CASE',c['id']);advice=c['body']['advice'][-1]
    assert advice['ai']['status']=='AVAILABLE' and advice['caseRevision']==c['revision']
    mutate(e,'CASE',c['id'],'reviews',dict(adviceVersion=1,text='您好，请提供问题照片供我们核实。',decision='ACCEPT',reason='逐项核对事实与政策'))
    persisted=read(e,'CASE',c['id']);assert persisted['state']=='HANDLED'
    assert persisted['body']['advice'][0]['ai']['output']['replyDraft']!=persisted['body']['reviews'][0]['text']
    from commerce_hub.scenarios.after_sales.service import AfterSales
    assert AfterSales(e.tasks,e.domain.source_reader).store.read(e.actor,'CASE',c['id'])['history']==persisted['history']
    mutate(e,'CASE',c['id'],'messages',dict(text='追加细节'))
    with pytest.raises(TaskError,match='STALE_ADVICE'):
        mutate(e,'CASE',c['id'],'reviews',dict(adviceVersion=1,text='旧稿',decision='ACCEPT',reason='拒绝旧稿'))
    with pytest.raises(TaskError,match='LINK_INVALID'):
        mutate(e,'CASE',c['id'],'links',dict(lineId='different-order-line',reason='纠正'))
    mutate(e,'CASE',c['id'],'messages',dict(text='充电线冒烟'))
    assert read(e,'CASE',c['id'])['state']=='ESCALATED'
    assert account_fingerprint(e.database,e.actor.tenant_id)==original
