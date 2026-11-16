"""Contract edge cases and recovery; fixtures are explicitly synthetic."""
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import update

from tests.integration.after_sales.test_workflows import env,dataset,case,read,mutate,run_job,publish_policies,golden,rehash,identities
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
def test_chunk_recovery_conflict_quarantine_and_new_dataset_version(env):
    e=env
    from commerce_hub.scenarios.after_sales.teaching import golden_package
    m,blocks=golden_package();d=e.domain.create_dataset(e.actor,uuid4().hex,dict(manifest=m))
    first=e.domain.upload(e.actor,d['id'],uuid4().hex,0,blocks[0],1)
    assert e.domain.upload(e.actor,d['id'],uuid4().hex,0,blocks[0],1)['revision']==first['revision']
    with pytest.raises(TaskError,match='CHUNK_CONFLICT'):e.domain.upload(e.actor,d['id'],uuid4().hex,0,[],1)
    with pytest.raises(TaskError,match='CHUNKS_MISSING'):mutate(e,'DATASET',d['id'],'seal')
    with pytest.raises(TaskError,match='DATASET_NOT_VERIFIED'):mutate(e,'DATASET',d['id'],'activate')
    for n,b in enumerate(blocks[1:],1):e.domain.upload(e.actor,d['id'],uuid4().hex,n,b,read(e,'DATASET',d['id'])['revision'])
    mutate(e,'DATASET',d['id'],'seal');run_job(e,'DATASET',d['id'],'validate')
    assert read(e,'DATASET',d['id'])['state']=='READBACK_VERIFIED'
    with pytest.raises(TaskError,match='DATASET_VERSION_EXISTS'):e.domain.create_dataset(e.actor,uuid4().hex,dict(manifest=m))
    m=deepcopy(m);m['version']='v2-late-events'
    newer=e.domain.create_dataset(e.actor,uuid4().hex,dict(manifest=m))
    assert newer['id']!=d['id'] and read(e,'DATASET',d['id'])['body']['manifest']['version']=='v1'


@pytest.mark.mysql
def test_model_failure_manual_path_policy_revocation_and_evidence_forgery(env):
    e=env;ds=dataset(e);publish_policies(e);c=case(e,ds)
    mutate(e,'CASE',c['id'],'links',dict(lineId='b-order-1-00-b-shirt',reason=''))
    run_job(e,'CASE',c['id'],'evidence');run_job(e,'CASE',c['id'],'advice')
    c=read(e,'CASE',c['id']);p=c['body']['advice'][-1]['policies'][0]
    mutate(e,'POLICY',p['policyId'],'revoke',dict(reason='该版本已失效'))
    with pytest.raises(TaskError,match='POLICY_NO_LONGER_AVAILABLE'):
        mutate(e,'CASE',c['id'],'reviews',dict(adviceVersion=1,text='不能采纳失效政策',decision='ACCEPT',reason='核实'))
    def failure(request):raise TimeoutError('synthetic provider failure')
    e.provider.invoke=failure
    run_job(e,'CASE',c['id'],'advice')
    c=read(e,'CASE',c['id']);assert c['body']['advice'][-1]['ai']['status']=='UNAVAILABLE'
    assert c['body']['evidence']['facts']
    mutate(e,'CASE',c['id'],'reviews',dict(adviceVersion=None,text='人工已核实，继续补证',decision='MANUAL',reason='模型不可用'))
    with pytest.raises(TaskError,match='EVIDENCE_REF_NOT_IN_SOURCE'):
        e.domain.investigation(e.actor,uuid4().hex,dict(kind='CASE',id=c['id'],text='伪造证据',evidenceRefs=['nonexistent']))
    assert read(e,'CASE',c['id'])['state']=='HANDLED'


@pytest.mark.mysql
def test_historical_risk_current_revoked_dataset_access_and_unknown_query(env):
    e=env;ds=dataset(e);result=run_job(e,'DATASET',ds['id'],'analysis',dict(ai=False));report=read(e,'REPORT',result['analysisReport']['domainRef']['id'])
    fid=report['body']['feedback'][0]['feedbackId']
    inv=e.domain.investigation(e.actor,uuid4().hex,dict(kind='REPORT',id=report['id'],text='人工核查',evidenceRefs=[fid]))
    mutate(e,'INVESTIGATION',inv['id'],'entries',dict(text='原文及实收支持调查',evidenceRefs=[fid],conclusion='SUPPORTED'))
    ti,ei=identities();risk=e.domain.risk(e.actor,uuid4().hex,dict(investigationId=inv['id'],reason='疑似描述偏差',limitations='教学数据',identity=ti,datasetId=ds['id']))
    mutate(e,'RISK',risk['id'],'decisions',dict(decision='CONFIRM',reason='人工确认',validUntil=None))
    run_job(e,'DATASET',ds['id'],'binding',dict(teachingIdentity=ti,erpIdentity=ei,validUntil=(timestamp(now())+timedelta(days=3)).isoformat()))
    port=QualityRiskReadPort(e.domain);item=ei|dict(warehouseId=ei['warehouseIds'][0]);saved=port.lookup(e.actor,[item]);assert saved[0]['status']=='MATCHED'
    mutate(e,'RISK',risk['id'],'decisions',dict(decision='CLOSE',reason='整改关闭',validUntil=None))
    assert port.lookup(e.actor,[item])[0]['status']=='NONE'
    assert port.historical(e.actor,saved)[0]['riskRefs'][0]['version']==2
    mutate(e,'DATASET',ds['id'],'deactivate')
    assert port.lookup(e.actor,[item])[0]['status']=='UNVERIFIED' and port.historical(e.actor,saved)[0]['riskRefs']==[]
    with pytest.raises(TaskError,match='DATASET_NOT_VERIFIED'):run_job(e,'DATASET',ds['id'],'analysis')


@pytest.mark.mysql
def test_new_analysis_keeps_original_and_records_rule_difference(env):
    e=env;ds=dataset(e);first=run_job(e,'DATASET',ds['id'],'analysis',dict(ai=False))
    rid=first['analysisReport']['domainRef']['id'];before=deepcopy(read(e,'REPORT',rid))
    changed=DEFAULT_RULE|dict(version='more-conservative',deltaBasisPoints=3000)
    second=run_job(e,'DATASET',ds['id'],'analysis',dict(ai=False,rule=changed,compareReportId=rid))
    report=read(e,'REPORT',second['analysisReport']['domainRef']['id'])
    assert report['body']['comparison']['comparable']
    assert report['body']['comparison']['changes']['ruleChanged']
    assert report['body']['metrics']['items'][0]['finding']=='NO_THRESHOLD_SIGNAL'
    assert read(e,'REPORT',rid)==before and before['body']['metrics']['items'][0]['finding']=='NEEDS_INVESTIGATION'


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
    from commerce_hub.scenarios.after_sales.teaching import policy_starters
    from commerce_hub.scenarios.after_sales.policies import validate_policy
    p={k:v for k,v in policy_starters()[0].items() if k!='id'}
    with pytest.raises(TaskError):validate_policy(p|change)
