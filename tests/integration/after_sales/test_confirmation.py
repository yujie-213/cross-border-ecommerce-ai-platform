"""Owned synthetic ERP transport + real isolated MySQL human confirmations."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from commerce_hub.adapters.erp import ERPConfig, ERPError
from commerce_hub.adapters.erp_customer_voice import TeachingVoiceClient
from commerce_hub.orchestration.service import TaskError
from commerce_hub.scenarios.after_sales.confirmation import Confirmation
from tests.support.b_source import BSourceERP
from tests.integration.after_sales.test_product_remediation import reader
from tests.integration.after_sales.test_workflows import env, read, run_job


def setup_case(e, tmp_path, erp):
    r=reader(tmp_path,erp)
    r.voice_client_factory=lambda:TeachingVoiceClient(ERPConfig(access_token='synthetic-only',interval=.1),transport=erp.transport,sleeper=lambda _:None)
    e.domain.source_reader=r
    for spec in e.specs.values():spec.handler.source_reader=r
    c=e.domain.create_case(e.actor,uuid4().hex,dict(title='尺码不合适',message='',region='CN',platform='TEACHING',language='zh',
        erpStoreName='Synthetic Store',erpVoiceId='71',erpVoiceKind='reviews'))
    run_job(e,'CASE',c['id'],'evidence')
    return read(e,'CASE',c['id'])


def confirm(e,c,key=None,text='您好，如果吊牌完整、未穿洗且符合退换货期限，可以申请换货或退货退款。请问吊牌是否保留、是否穿洗过呢？'):
    return e.domain.mutate(e.actor,'CASE',c['id'],'reviews',key or uuid4().hex,c['revision'],
        dict(adviceVersion=None,text=text,decision='MANUAL',reason='客服核对事实及政策后确认'))


@pytest.mark.mysql
def test_confirm_readback_audit_and_replay(env,tmp_path):
    e=env;erp=BSourceERP();c=setup_case(e,tmp_path,erp);key=uuid4().hex
    assert erp.voice_writes==0
    result=confirm(e,c,key);assert result['state']=='HANDLED' and result['handlingStatus']=='CONFIRMED'
    assert confirm(e,c,key)==result and erp.voice_writes==1
    saved=read(e,'CASE',c['id']);review=saved['body']['reviews'][-1]
    assert review['externalAction']=='ERP_INTERNAL_HANDLING' and review['erpRecord']['version']==1
    assert saved['body']['confirmation']['originalMessages']==c['body']['messages']
    assert saved['body']['confirmation']['actor']==e.actor.principal_id
    assert erp.voices['reviews'][0]['body']=='尺寸偏小，请核对描述'
    with pytest.raises(TaskError,match='COMMAND_CONFLICT'):confirm(e,c,key,text='不同正文')


@pytest.mark.mysql
@pytest.mark.parametrize('failure',['before','after'])
def test_unknown_never_resends_and_recovers_original(env,tmp_path,failure):
    e=env;erp=BSourceERP();c=setup_case(e,tmp_path,erp);key=uuid4().hex;erp.voice_failure=failure
    assert confirm(e,c,key)['handlingStatus']=='PENDING'
    assert read(e,'CASE',c['id'])['state']!='HANDLED'
    assert not read(e,'CASE',c['id'])['body']['reviews']
    erp.voice_failure=None
    result=Confirmation(e.domain).recover(e.actor,key,c['id'])
    assert result['handlingStatus']==('CONFIRMED' if failure=='after' else 'PENDING')
    assert erp.voice_writes==1
    if failure=='before':
        with pytest.raises(TaskError,match='CONFIRMATION_PENDING'):
            confirm(e,read(e,'CASE',c['id']))


@pytest.mark.mysql
def test_rejected_does_not_complete_and_can_be_corrected(env,tmp_path):
    e=env;erp=BSourceERP();c=setup_case(e,tmp_path,erp);erp.voice_failure='reject'
    assert confirm(e,c)['handlingStatus']=='REJECTED'
    current=read(e,'CASE',c['id']);assert current['state']!='HANDLED' and not current['body']['reviews']
    erp.voice_failure=None;assert confirm(e,current)['state']=='HANDLED'


@pytest.mark.mysql
def test_readback_missing_and_local_commit_failure_preserve_recovery(env,tmp_path,monkeypatch):
    e=env;erp=BSourceERP();c=setup_case(e,tmp_path,erp);key=uuid4().hex
    erp.voice_hide_history=True
    assert confirm(e,c,key)['handlingStatus']=='PENDING'
    erp.voice_hide_history=False
    original=e.domain.store.save
    def fail_final(conn,actor,row,body,state=None):
        if state=='HANDLED':raise RuntimeError('synthetic-local-commit-failure')
        return original(conn,actor,row,body,state)
    monkeypatch.setattr(e.domain.store,'save',fail_final)
    with pytest.raises(RuntimeError,match='synthetic-local-commit-failure'):Confirmation(e.domain).recover(e.actor,key,c['id'])
    assert read(e,'CASE',c['id'])['state']!='HANDLED'
    monkeypatch.setattr(e.domain.store,'save',original)
    assert Confirmation(e.domain).recover(e.actor,key,c['id'])['state']=='HANDLED'
    assert erp.voice_writes==1


@pytest.mark.mysql
def test_concurrent_confirmation_different_keys_writes_once(env,tmp_path):
    e=env;erp=BSourceERP();c=setup_case(e,tmp_path,erp);entered=Event();release=Event()
    transport=erp.transport
    def pause(method,target,*args):
        if method=='POST' and target=='/api/v1/customer-voice':
            entered.set();assert release.wait(5)
        return transport(method,target,*args)
    e.domain.source_reader.voice_client_factory=lambda:TeachingVoiceClient(ERPConfig(access_token='synthetic-only'),transport=pause,sleeper=lambda _:None)
    with ThreadPoolExecutor(2) as pool:
        first=pool.submit(confirm,e,c);assert entered.wait(5)
        try:
            with pytest.raises(TaskError,match='REVISION_CONFLICT|CONFIRMATION_PENDING'):confirm(e,read(e,'CASE',c['id']))
        finally:release.set()
        assert first.result()['state']=='HANDLED'
    assert erp.voice_writes==1


@pytest.mark.mysql
def test_current_ai_original_and_human_final_survive_confirmation(env,tmp_path):
    import json
    from tests.integration.after_sales.test_workflows import publish_policies
    e=env;erp=BSourceERP();c=setup_case(e,tmp_path,erp);publish_policies(e)
    original=e.provider.invoke
    draft='您好，如果吊牌完整、未穿洗且符合退换货期限，可以申请换货或退货退款。请问衣服是否穿洗过、吊牌是否完整呢？'
    def customer_reply(request):
        result=original(request)
        if request.control.purpose=='b.case.advice.v1':
            assert '直接对客户说的可发送回复正文' in request.payload.messages[0].content
            data=json.loads(request.payload.messages[1].content)
            assert any('吊牌完整' in p['text'] for p in data['policies'])
            output=json.loads(result.content);output['replyDraft']=draft
            result=result.model_copy(update=dict(content=json.dumps(output,ensure_ascii=False)))
        return result
    e.provider.invoke=customer_reply
    run_job(e,'CASE',c['id'],'advice');c=read(e,'CASE',c['id'])
    assert c['body']['advice'][-1]['ai']['status']=='AVAILABLE'
    final=draft+'我们会继续协助您。'
    result=e.domain.mutate(e.actor,'CASE',c['id'],'reviews',uuid4().hex,c['revision'],dict(
        adviceVersion=c['body']['advice'][-1]['version'],text=final,decision='ACCEPT',reason='客服核对并修改回复'))
    assert result['state']=='HANDLED'
    saved=read(e,'CASE',c['id'])['body']
    assert saved['confirmation']['aiOriginal']['ai']['output']['replyDraft']==draft
    assert saved['reviews'][-1]['text']==final and erp.voice_writes==1


def test_adapter_rejects_other_resource_and_oversized_payload():
    client=TeachingVoiceClient(ERPConfig(access_token='synthetic-only'),transport=lambda *args:pytest.fail('must not send'))
    for args in [('tickets','91',0,'正文','key'),('reviews','71',0,'x'*2001,'key'),('reviews','0',0,'正文','key')]:
        with pytest.raises(ERPError,match='ERP_VOICE_PAYLOAD_REJECTED'):client.append(*args)


def test_direct_customer_reply_is_supported_but_internal_instructions_are_rejected():
    from commerce_hub.scenarios.after_sales.policies import validate_advice, retrieve
    from commerce_hub.scenarios.after_sales.teaching import policy_starters
    policy=policy_starters('US','Amazon')[0]
    refs=retrieve([dict(id='policy',revision=3,state='PUBLISHED',body=policy)],dict(identity=dict(category='APPAREL'),region='US',platform='Amazon',language='zh',
        messages=[dict(text='尺码不合适，想退换')]),'2026-11-17T00:00:00Z')
    output=dict(replyDraft='您好，如果吊牌完整、未穿洗且在退换货期限内，可以申请换货或退货退款。请问衣服是否穿洗过、吊牌是否完整呢？',
        adviceCode='CLARIFY',citations=[{k:refs[0][k] for k in ('policyId','version','sectionId','hash')}],missingEvidence=['吊牌及穿洗情况'],escalation=False)
    assert validate_advice(output,refs)==output
    with pytest.raises(TaskError,match='INTERNAL_INSTRUCTION_IN_REPLY'):
        validate_advice(output|dict(replyDraft='建议客服先核实吊牌，然后指导客户申请退货。'),refs)
    with pytest.raises(TaskError,match='UNSUPPORTED_PROMISE'):
        validate_advice(output|dict(replyDraft='已退款，请查收。'),refs)
