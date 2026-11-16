"""Self-created ERP membership is enforced server-side, including old links."""
from types import SimpleNamespace
from uuid import uuid4
import json
import pytest
from commerce_hub.orchestration.service import TaskError
from tests.integration.after_sales.test_product_remediation import reader
from tests.integration.after_sales.test_workflows import env,run_job,read,dataset
from tests.support.b_source import BSourceERP


def members():
    return [SimpleNamespace(storeName='Synthetic Store',sourceTenant='1',sourceStore='1',sourceWarehouse='1',sku='V2-SKU-0',
        monitor=SimpleNamespace(productId='1',salesIds=('81',),datasetId='synthetic-owned',scopeVersion=1))]


def owned(tmp_path,erp=None):
    r=reader(tmp_path,erp);r.owned_provider=members;return r


def test_inbox_excludes_shared_sku_and_unregistered_order(tmp_path):
    erp=BSourceERP();erp.voices['reviews'].append(erp.voices['reviews'][0] | dict(id=99,sku='V2-SKU-1',body='other data'))
    erp.voices['feedback'].append(erp.voices['feedback'][0] | dict(id=98,order_id=999))
    erp.tickets.append(erp.tickets[0] | dict(id=97,order_sn='OTHER'))
    r=owned(tmp_path,erp)
    assert [i['recordId'] for i in r.inbox('Synthetic Store','reviews',lambda:None)['items']]==['71']
    assert [i['recordId'] for i in r.inbox('Synthetic Store','feedback',lambda:None)['items']]==['72']
    assert [i['ticketId'] for i in r.discover('Synthetic Store',lambda:None)['items']]==['91']
    assert r.voice_evidence('71','reviews','Synthetic Store',lambda:None,'own')['identity']['productId']=='1'
    assert r.evidence('91','Synthetic Store',lambda:None,'ticket')['identity']['orderId']=='81'
    for rid,kind in [('99','reviews'),('98','feedback')]:
        with pytest.raises(TaskError,match='SOURCE_NOT_OWNED'):r.voice_evidence(rid,kind,'Synthetic Store',lambda:None,'denied')
    with pytest.raises(TaskError,match='SOURCE_NOT_OWNED'):r.evidence('97','Synthetic Store',lambda:None,'denied')


def test_exact_product_and_store_warehouse_binding_not_prefix(tmp_path):
    r=owned(tmp_path)
    good=dict(sourceTenant='1',productId='1',sku='V2-SKU-0',storeId='1',warehouseIds=['1'])
    assert r.allows_identity(good)
    for change in [dict(productId='2'),dict(storeId='2'),dict(sourceTenant='2'),dict(warehouseIds=['2']),dict(sku='V2-SKU-0-copy')]:
        assert not r.allows_identity(good | change)
    r.owned_provider=lambda:[]
    with pytest.raises(TaskError,match='SOURCE_SCOPE_DENIED'):r.inbox('Synthetic Store','reviews',lambda:None)


@pytest.mark.mysql
def test_old_case_direct_links_lists_and_new_admission_follow_current_membership(env,tmp_path):
    e=env;erp=BSourceERP();r=owned(tmp_path,erp);e.domain.source_reader=r
    for spec in e.specs.values():spec.handler.source_reader=r
    data=dict(title='自建评价',message='',region='CN',platform='TEACHING',language='zh',erpStoreName='Synthetic Store',erpVoiceId='71',erpVoiceKind='reviews')
    c=e.domain.create_case(e.actor,uuid4().hex,data)
    assert read(e,'CASE',c['id'])['body']['sourceMembership'][0]['productId']=='1'
    run_job(e,'CASE',c['id'],'evidence')
    r.owned_provider=lambda:[]
    assert e.domain.store.list(e.actor,'CASE')['items']==[]
    with pytest.raises(TaskError,match='NOT_FOUND'):read(e,'CASE',c['id'])
    with pytest.raises(TaskError,match='SOURCE_SCOPE_DENIED'):e.domain.create_case(e.actor,uuid4().hex,data)


@pytest.mark.mysql
def test_product_ai_receives_only_its_feedback_and_metrics(env):
    e=env;d=dataset(e);contexts=[];original=e.provider.invoke
    def inspect(request):
        if request.control.purpose=='b.experience.explain.v1':contexts.append(json.loads(request.payload.messages[1].content))
        return original(request)
    e.provider.invoke=inspect
    result=run_job(e,'DATASET',d['id'],'analysis',dict(ai=True))
    report=read(e,'REPORT',result['analysisReport']['domainRef']['id'])
    assert len(contexts)==len(report['body']['metrics']['items'])
    for context in contexts:
        pid=context['metrics']['items'][0]['productId']
        assert all(f['productId']==pid for f in context['feedback'])
        assert all(not ref.startswith('metric:') or ref.split(':')[1]==pid for ref in context['factRefs'])
        assert report['body']['productAI'][pid]['status']=='AVAILABLE'
