"""Contract edge cases and recovery; fixtures are explicitly synthetic."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update

from tests.integration.after_sales.test_workflows import env,erp_case,read,mutate,run_job,publish_policies,golden,rehash
from commerce_hub.scenarios.after_sales.common import digest,now,timestamp
from commerce_hub.scenarios.after_sales.risk import QualityRiskReadPort
from commerce_hub.orchestration.service import TaskError
from commerce_hub.capabilities.metrics.after_sales import analyze,DEFAULT_RULE


def test_split_batches_duplicate_reference_counts_and_exact_threshold():
    m,r=golden();ship=next(x for x in r if x['type']=='shipment')
    ship['quantity']=1
    second=deepcopy(ship);second.update(id='second-batch',batchId='second-actual',at='2026-08-01T01:00:00Z');r.append(second)
    alias=deepcopy(ship);alias['id']='another-reference-to-same-batch';r.append(alias);rehash(m,r)
    report=analyze(r,m,m['windows'],m['asOf'])
    assert report['items'][0]['groups'][0]['denominator']==40
    exact=DEFAULT_RULE|dict(deltaBasisPoints=2750)
    assert analyze(r,m,m['windows'],m['asOf'],exact)['items'][0]['finding']=='NEEDS_INVESTIGATION'
    assert analyze(r,m,m['windows'],m['asOf'],exact|dict(deltaBasisPoints=2751))['items'][0]['finding']=='NO_THRESHOLD_SIGNAL'
    alias['quantity']=2
    with pytest.raises(TaskError,match='DUPLICATE_BATCH_CONFLICT'):analyze(r,m,m['windows'],m['asOf'])


def test_cancelled_draft_late_received_and_currency_are_not_received_twice():
    m,r=golden();events=[x for x in r if x['type']=='return' and 'b-order-1-00-b-shirt'==x['lineId']]
    # Authorized in the 30-day window; receipt occurs outside, refund separately.
    next(x for x in events if x['stage']=='received')['at']='2026-10-05T00:00:00Z'
    next(x for x in events if x['stage']=='refunded')['at']='2026-10-06T00:00:00Z'
    result=analyze(r,m,m['windows'],m['asOf'])['items'][0]['groups'][1]
    assert result['numerator']==10 and result['stages']['authorizedValid']==12
    assert result['outsideWindow'] and result['refundAmounts']['CNY']=='200'
    m,r=golden();events=[x for x in r if x['type']=='return' and 'b-order-1-00-b-shirt'==x['lineId']]
    r=[x for x in r if x not in events or x['stage'] in {'requested','authorized'}]
    cancelled=deepcopy(events[1]);cancelled.update(id='cancelled',stage='cancelled',at='2026-09-05T00:00:00Z');r.append(cancelled);rehash(m,r)
    result=analyze(r,m,m['windows'],m['asOf'])['items'][0]['groups'][1]
    assert result['numerator']==10 and result['stages']['authorizedValid']==10 and result['stages']['cancelled']==2




@pytest.mark.mysql
def test_model_failure_manual_path_policy_revocation_and_evidence_forgery(env):
    e=env;publish_policies(e);c=erp_case(e)
    run_job(e,'CASE',c['id'],'evidence');run_job(e,'CASE',c['id'],'advice')
    c=read(e,'CASE',c['id']);p=c['body']['advice'][-1]['policies'][0]
    
    for policy in e.domain.store.list(e.actor,'POLICY',limit=100)['items']:
        mutate(e,'POLICY',policy['id'],'revoke',dict(reason='该版本已失效'))
    with pytest.raises(TaskError,match='POLICY_NO_LONGER_AVAILABLE'):
        mutate(e,'CASE',c['id'],'reviews',dict(adviceVersion=1,text='不能采纳失效政策',decision='ACCEPT',reason='核实'))
    def failure(request):raise TimeoutError('synthetic provider failure')
    publish_policies(e)
    e.provider.invoke=failure
    run_job(e,'CASE',c['id'],'advice')
    c=read(e,'CASE',c['id']);assert c['body']['advice'][-1]['ai']['status']=='UNAVAILABLE'
    assert c['body']['evidence']['facts']
    mutate(e,'CASE',c['id'],'reviews',dict(adviceVersion=None,text='人工已核实，继续补证',decision='MANUAL',reason='模型不可用'))
    with pytest.raises(TaskError,match='EVIDENCE_REF_NOT_IN_SOURCE'):
        e.domain.investigation(e.actor,uuid4().hex,dict(kind='CASE',id=c['id'],text='伪造证据',evidenceRefs=['nonexistent']))
    assert read(e,'CASE',c['id'])['state']=='HANDLED'






def test_erp_projection_bounded_multi_line_missing_domain_never_auto_links(tmp_path):
    from types import SimpleNamespace
    from commerce_hub.scenarios.after_sales.source import SourceReader
    class Reader:
        def detail(self,kind,rid):
            if kind=='customer-tickets':return dict(id=rid,tenant_id=1,store_name='Store',subject='仅标题',order_sn='EXACT-ORDER',platform='P')
            raise TaskError('FULFILLMENT_UNAVAILABLE')
        def read(self,path,parameters,**kwargs):
            if path.endswith('sales-orders'):
                records=[dict(id=10,order_sn='EXACT-ORDER',tenant_id=1,store_name='Store',payment_status='已支付',item_list=[dict(sku='SKU')]*20)]
            else:records=[dict(id=11,tenant_id=1,sku='SKU',name='已关联商品')]
            return SimpleNamespace(records=records,complete=True)
    source=SourceReader(Reader,{'Store':dict(storeId='1',sourceTenant='1')},tmp_path)
    facts=source.evidence('9','Store',lambda:None,'test')
    assert facts['identity'] is None and len(facts['identityCandidates'])==10
    assert len(facts['facts'])==2 and any('10行' in m for m in facts['missing'])
    assert any('FULFILLMENT_UNAVAILABLE' in m for m in facts['missing'])


@pytest.mark.parametrize('change',[dict(sections=[None]),dict(terms=[[]]),dict(topics='size'),dict(title=[]),dict(category=[])])
def test_malformed_policies_have_domain_error_not_server_exception(change):
    from commerce_hub.scenarios.after_sales.policy_templates import policy_starters
    from commerce_hub.scenarios.after_sales.policies import validate_policy
    p={k:v for k,v in policy_starters()[0].items() if k!='id'}
    with pytest.raises(TaskError):validate_policy(p|change)
