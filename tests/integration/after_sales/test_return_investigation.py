"""Real domain/HTTP/MySQL and Worker; ERP and model are synthetic adapters."""
from types import SimpleNamespace
from uuid import uuid4
import json
import pytest
from fastapi.testclient import TestClient
from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.scenarios.after_sales.source import SourceReader
from commerce_hub.scenarios.after_sales.risk import QualityRiskReadPort
from commerce_hub.orchestration.service import TaskError
from tests.integration.after_sales.test_workflows import env,read,mutate,run_job
from tests.support.b_returns import ReturnERP


@pytest.mark.mysql
def test_return_and_trend_merge_manual_evidence_ai_confirmation_and_revoke(env,tmp_path):
    e=env;erp=ReturnERP()
    member=SimpleNamespace(storeName='Owned Store',sku='SKU-KNIT',sourceTenant='1',sourceStore='2',sourceWarehouse='20',warehouseName='WH-A',
        monitor=SimpleNamespace(productId='10',salesIds=tuple(str(o['id']) for o in erp.orders)))
    r=SourceReader(lambda:erp,{'Owned Store':dict(sourceTenant='1',storeId='2')},tmp_path,owned_provider=lambda:[member])
    e.domain.source_reader=r
    for spec in e.specs.values():spec.handler.source_reader=r
    with TestClient(create_app(e.settings,e.specs)) as client:
        client.headers['Authorization']='Bearer '+e.token
        def post(path,data):
            response=client.post('/api/b/v1'+path,json=data,headers={'Idempotency-Key':uuid4().hex})
            assert response.status_code==200,response.text
            return response.json()
        snapshot=client.get('/api/b/v1/return-analysis',params=dict(store='Owned Store',endDate='2026-11-17')).json()
        assert snapshot['monitor'][0]['currentReturnRate']==24
        origin=post('/return-cases',dict(store='Owned Store',returnId='902',sku='SKU-KNIT'))
        facts=read(e,'CASE',origin['id'])['body']['evidence']['facts']
        inv=post('/investigations',dict(kind='CASE',id=origin['id'],text='接缝开线调查',evidenceRefs=[facts[0]['id']]))
        trend=post('/monitor-cases',dict(store='Owned Store',sku='SKU-KNIT',endDate='2026-11-17',windowDays=7))
        trendfacts=read(e,'CASE',trend['id'])['body']['evidence']['facts']
        same=post('/investigations',dict(kind='CASE',id=trend['id'],text='退货率上升，追加趋势证据',evidenceRefs=[trendfacts[0]['id']]))
        assert same['id']==inv['id']
        run_job(e,'CASE',trend['id'],'evidence')  # refresh uses the return/monitor adapter, not tickets
        mutate(e,'INVESTIGATION',inv['id'],'evidence',dict(text='抽检两件袖口均有开线，照片见质检记录。',sourceRef='QC-20261117-002'))
        proof=client.get('/api/b/v1/investigations/'+inv['id']+'/facts').json()['items']
        assert any(f['domain']=='SKU_MONITOR' for f in proof)
        manual=next(f for f in proof if f['domain']=='MANUAL_EVIDENCE')
        captured=[];original=e.provider.invoke
        def capture(request):
            captured.append(json.loads(request.payload.messages[1].content));return original(request)
        e.provider.invoke=capture
        run_job(e,'CASE',origin['id'],'investigation',dict(investigationId=inv['id']))
        assert any(f['ref']==manual['id'] for f in captured[-1]['facts'])
        assert read(e,'CASE',origin['id'])['body']['investigationAssists'][-1]['ai']['status']=='AVAILABLE'
        identity=dict(sourceTenant='1',productId='10',sku='SKU-KNIT',storeId='2',warehouseMode='ALL_STORE_WAREHOUSES',warehouseIds=[])
        target=dict(sourceTenant='1',productId='10',sku='SKU-KNIT',storeId='2',warehouseId='20')
        assert QualityRiskReadPort(e.domain).lookup(e.actor,[target])[0]['status']!='MATCHED'
        # Evidence without a human conclusion never enables the reminder.
        with pytest.raises(TaskError,match='INVESTIGATION_CONCLUSION_REQUIRED'):
            e.domain.confirm_risk(e.actor,inv['id'],uuid4().hex,read(e,'INVESTIGATION',inv['id'])['revision'],dict(reason='接缝缺陷',limitations='限本店同款',identity=identity,validUntil=None))
        mutate(e,'INVESTIGATION',inv['id'],'entries',dict(text='实物抽检支持接缝质量风险',evidenceRefs=[manual['id']],conclusion='SUPPORTED'))
        revision=read(e,'INVESTIGATION',inv['id'])['revision'];key=uuid4().hex
        payload=dict(expectedRevision=revision,data=dict(reason='接缝质量风险',limitations='限本店同款',identity=identity,validUntil=None))
        response=client.post('/api/b/v1/investigations/'+inv['id']+'/confirm-risk',json=payload,headers={'Idempotency-Key':key})
        assert response.status_code==200,response.text
        risk=response.json();assert risk['state']=='CONFIRMED'
        assert client.post('/api/b/v1/investigations/'+inv['id']+'/confirm-risk',json=payload,headers={'Idempotency-Key':key}).json()==risk
        assert read(e,'RISK',risk['id'])['body']['confirmedEvidence'][0]['sourceRef']=='QC-20261117-002'
        assert QualityRiskReadPort(e.domain).lookup(e.actor,[target])[0]['status']=='MATCHED'
        assert QualityRiskReadPort(e.domain).lookup(e.actor,[target|dict(storeId='3')])[0]['status']!='MATCHED'
        mutate(e,'RISK',risk['id'],'decisions',dict(decision='REVOKE',reason='复检后撤销',validUntil=None))
        assert QualityRiskReadPort(e.domain).lookup(e.actor,[target])[0]['status']!='MATCHED'
