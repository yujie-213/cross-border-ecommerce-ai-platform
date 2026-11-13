"""Normal online workflow with protocol fixtures and real O01/G02/MySQL controls."""
from dataclasses import replace
from decimal import Decimal
from threading import Event
from uuid import uuid4
import json
import pytest
from commerce_hub.orchestration.service import SharedModelAuthorization
from commerce_hub.orchestration.worker import Worker,ExecutionContext
from commerce_hub.orchestration.budget import BudgetError
from commerce_hub.capabilities.models.gateway import ModelGateway
from commerce_hub.capabilities.models.contracts import ProviderResult,Usage
from commerce_hub.scenarios.s01_backend import S01BackendHandler
from commerce_hub.scenarios.s01.natural_explanation import bundle_for_result
from tests.integration.orchestration.test_s01_reports import make_s01,count
from tests.integration.s01.test_online_workflow import environment
from commerce_hub.orchestration.tables import attempts
from commerce_hub.governance.observability.tables import usage_facts

pytestmark=pytest.mark.mysql

class NaturalProvider:
    def __init__(self,mode='success'):self.calls=0;self.mode=mode
    def describe_capabilities(self):return frozenset({'structured_output'})
    def preflight(self,*_):pass
    def invoke(self,request):
        self.calls+=1
        output={k:[] for k in ['recommendationReasons','keyEvidence','majorRisks','humanConfirmations']}
        facts=json.loads(request.payload.messages[1].content)['facts']
        for fact in facts:
            for section in fact['requiredSections']:
                output[section].append(dict(text=fact['allowedPhrases'][0],supportRefs=[fact['ref']]))
        if self.mode=='invalid':output['keyEvidence'][0]['text']='库存足够，采购已批准'
        return ProviderResult(status='COMPLETED',finishReason='stop',content=json.dumps(output,ensure_ascii=False),
            actualModelRevision=request.payload.modelRevision,usage=Usage(inputTokens=900,outputTokens=100))

def with_provider(make_s01,mode='success',calls=1):
    env=environment(make_s01);provider=NaturalProvider(mode)
    env.spec.handler.gateway=ModelGateway(provider,timeout_seconds=5)
    authorization=SharedModelAuthorization('online-test-'+uuid4().hex,calls,100000,Decimal('1'))
    env.spec=replace(env.spec,max_calls=1,max_tokens=24000,max_cost=Decimal('.05'),policy_version=authorization.authorization_id,
        cost_currency='USD',shared_model_authorization=authorization)
    env.service.registry={env.spec.scenario_id:env.spec}
    return env,provider

@pytest.mark.parametrize('mode',['success','invalid'])
def test_current_online_limits_are_explained_without_inventing_a_business_baseline(make_s01,mode):
    env,p=with_provider(make_s01,mode);tid=env.submit('model')['taskRef']['taskId'];assert Worker(env.service).once()
    report=env.service.read_report(env.principal,tid);ai=report['analysisReport']['ai']
    assert report['completeness']=='BLOCKED' and report['dataReport']['supplyDemand']['baseline'] is None
    assert ai['status']==('AVAILABLE' if mode=='success' else 'UNAVAILABLE')
    assert ai['usage']['totalTokens']==1000 and ai['costStatus']=='UNKNOWN'
    assert ai['binding']['snapshotId']==report['snapshotRef']
    assert count(env,usage_facts)==1 and count(env,attempts)==1 and p.calls==1
    env.submit('model');env.service.read_report(env.principal,tid)
    assert not Worker(env.service).once() and p.calls==1
    if mode=='success':
        text=json.dumps(ai['explanation'],ensure_ascii=False)
        assert '无法确定' in text or '未知' in text
        assert '质量' in text and '阻断' in text

def test_shared_call_budget_survives_new_tasks_and_new_gateway_instances(make_s01):
    env,p=with_provider(make_s01)
    tid=env.submit('one')['taskRef']['taskId'];assert Worker(env.service).once()
    assert env.service.read_report(env.principal,tid)['analysisReport']['ai']['status']=='AVAILABLE'
    # Simulated restart: a new provider/gateway cannot reset O01's group policy.
    replacement=NaturalProvider();env.spec.handler.gateway=ModelGateway(replacement)
    tid2=env.submit('two')['taskRef']['taskId'];assert Worker(env.service).once()
    ai=env.service.read_report(env.principal,tid2)['analysisReport']['ai']
    assert ai['status']=='UNAVAILABLE' and ai['reason']=='MODEL_ALLOWANCE_UNAVAILABLE'
    assert replacement.calls==0 and p.calls==1

def test_token_risk_is_aggregated_across_original_tasks(make_s01):
    env,p=with_provider(make_s01,calls=2)
    shared=replace(env.spec.shared_model_authorization,max_tokens=1000)
    env.spec=replace(env.spec,shared_model_authorization=shared);env.service.registry={env.spec.scenario_id:env.spec}
    env.submit('a');env.submit('b');handles=[]
    for _ in range(2):
        lease=env.queue.claim([env.spec.work_kind]);row=env.service.start(lease,env.principal)
        handles.append(ExecutionContext(env.service,lease,env.principal,row,Event()).budget)
    handles[0].reserve('call-a','attempt-a',600,'.05')
    with pytest.raises(BudgetError,match='BUDGET_DENIED'):handles[1].reserve('call-b','attempt-b',600,'.05')
    handles[0].release_unsent('attempt-a')
    handles[1].reserve('call-b','attempt-b',600,'.05')

def test_authorization_serializes_provider_send_and_keeps_unknown_reserved(make_s01):
    env,p=with_provider(make_s01,calls=2);env.submit('a');env.submit('b');handles=[]
    for _ in range(2):
        lease=env.queue.claim([env.spec.work_kind]);row=env.service.start(lease,env.principal)
        handles.append(ExecutionContext(env.service,lease,env.principal,row,Event()).budget)
    for n,handle in enumerate(handles):handle.reserve(f'call-{n}',f'attempt-{n}',2000,'.05')
    handles[0].send_model('attempt-0','call-0',max_inflight=1,details={},trace_id='test')
    with pytest.raises(BudgetError,match='CONCURRENCY_DENIED'):
        handles[1].send_model('attempt-1','call-1',max_inflight=1,details={},trace_id='test')
    handles[0].unknown('attempt-0')
    with pytest.raises(BudgetError,match='USAGE_MUST_BE_RECONCILED'):
        handles[1].send_model('attempt-1','call-1',max_inflight=1,details={},trace_id='test')
