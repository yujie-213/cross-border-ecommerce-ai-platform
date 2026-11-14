"""Actual isolated MySQL, synthetic ERP; not real business acceptance."""
from copy import deepcopy
from datetime import datetime,timezone
import json
from uuid import uuid4
import pytest
from sqlalchemy import select,update
from commerce_hub.data.projection.monitor import MonitorRegistry,monitor_scopes
from commerce_hub.data.sync.v2 import V2Reader
from commerce_hub.data.sync.v2_store import AcquisitionCheckpoint,acquisitions
from commerce_hub.scenarios.s01_v2.store import ItemStore
from commerce_hub.orchestration.worker import Worker
from commerce_hub.adapters.erp import ERPConfig
from tests.unit.data.test_owned import owned_case
from tests.integration.s01.test_v2_workflow import environment,run
from tests.integration.orchestration.test_s01_reports import make_s01

pytestmark=pytest.mark.mysql


def revision(database):
    m,_,_=owned_case();m=m.model_copy(update={'scope':dict(m.scope,tenantId='checkpoint-'+uuid4().hex)})
    registry=MonitorRegistry(database.engine,m.scope['tenantId']);old=m.model_dump(mode='json');digest=registry.activate([old],'fixture-importer')
    new=deepcopy(old);new['monitor']['scopeVersion']=2
    new['monitor']['stockCheckpoint']=dict(version=1,inventoryId='7',quantity='6',available='6',observedAt='2026-11-13T05:10:00Z',
        postedAt='2026-11-13T05:00:06Z',lastEventId='206',evidenceDigest='a'*64,historyDisposition='Synthetic independently verified checkpoint; retain earlier history')
    return registry,old,new,digest


def test_versioned_checkpoint_atomic_revision_preserves_prior_content(database):
    registry,old,new,digest=revision(database)
    registry.revise_checkpoint([new],'fixture-importer',digest)
    with database.engine.connect() as c:rows=c.execute(select(monitor_scopes).filter_by(tenant_id=registry.tenant_id).order_by(monitor_scopes.c.scope_version)).mappings().all()
    assert len(rows)==2 and rows[0]['content']==[old] and not rows[0]['active'] and rows[1]['active']
    assert registry.mappings()[0].monitor.stockCheckpoint.quantity==6
    with pytest.raises(ValueError,match='CHECKPOINT_REVISION_CONFLICT'):registry.revise_checkpoint([new],'fixture-importer',digest)


@pytest.mark.parametrize('fault',['digest','membership','watermark','version','duplicate'])
def test_checkpoint_rejects_invalid_revision_without_mutating_active_scope(database,fault):
    registry,old,new,digest=revision(database)
    if fault=='digest':digest='b'*64
    if fault=='membership':new['monitor']['openingQuantity']='999'
    if fault=='watermark':new['monitor']['stockCheckpoint']['postedAt']='2026-11-14T05:00:00Z'
    if fault=='version':new['monitor']['stockCheckpoint']['version']=5
    values=[new,new] if fault=='duplicate' else [new]
    with pytest.raises(ValueError):registry.revise_checkpoint(values,'fixture-importer',digest)
    assert registry.mappings()[0].model_dump(mode='json')==old


def test_runtime_report_persistence_and_new_failure_does_not_overwrite_history(make_s01,tmp_path):
    e=environment(make_s01,tmp_path,2);first,report=run(e)
    with e.database.engine.connect() as c:items=ItemStore.read(c,e.tenant,first)
    assert all(r['admissionVersion']=='s01-runtime-v1' for r in items.values())
    assert all(r['capabilities']['requisition']['enabled'] for r in items.values())
    e.erp.data['quotes'][0]['status']='expired'
    second=e.service.create(e.principal,'next','S01_V2_BATCH',e.scope,{},'synthetic')['taskRef']['taskId']
    assert Worker(e.service).once()
    with e.database.engine.connect() as c:new=ItemStore.read(c,e.tenant,second)
    assert any(not r['capabilities']['requisition']['enabled'] for r in new.values())
    assert e.service.read_report(e.principal,first)==report
    assert len(e.service.history(e.principal,e.scope,scenario_id='S01_V2_BATCH')['items'])==2


def test_old_checkpoint_recovery_keeps_original_admission_version(make_s01,tmp_path):
    from tests.support.v2 import MemoryCheckpoint,SyntheticERP
    erp=SyntheticERP(1);cp=MemoryCheckpoint();cp.value.update(startedAt='2026-11-13T06:00:00+00:00',resources={},events=[])
    reader=erp.reader(tmp_path,cp)
    assert 'admissionVersion' not in reader.state
    from commerce_hub.data.sync.v2_catalog import collect_catalog
    from commerce_hub.data.projection.v2 import entities
    from commerce_hub.scenarios.s01_v2.analysis import analyze
    catalog=collect_catalog(reader,'1');item=analyze(catalog,entities(catalog,'1')[0],reader)
    assert 'admissionVersion' not in item and item['sourceGrade']=='REFERENCE_ONLY'


def admitted_environment(make_s01,tmp_path,monkeypatch):
    from tests.support.admission_runtime import AdmissionERP
    import commerce_hub.data.sync.v2 as v2
    monkeypatch.setattr(v2,'now',lambda:'2026-11-13T06:00:05+00:00')
    e=environment(make_s01,tmp_path,1);e.erp=AdmissionERP();e.policy.owned_mappings=[]
    return e


def test_runtime_positive_rules_are_sealed_and_compatible_api_fields_survive_restart(make_s01,tmp_path,monkeypatch,mysql_settings):
    from fastapi.testclient import TestClient
    from pydantic import SecretStr
    import jwt
    from commerce_hub.entrypoints.http.app import create_app
    e=admitted_environment(make_s01,tmp_path,monkeypatch);tid,report=run(e)
    with e.database.engine.connect() as c:item=next(iter(ItemStore.read(c,e.tenant,tid).values()))
    assert item['quantity']==48 and item['capabilities']['risk']['enabled'] and item['capabilities']['rules']['enabled']
    assert item['inventoryBasis']['residual']=='0' and item['demandWindow']['validDays']==7
    settings=mysql_settings.model_copy(update=dict(environment='test',auth_issuer='fixture-issuer',auth_audience='fixture-audience',
        auth_signing_key=SecretStr('fixture-key-'+'x'*64),browser_origin='https://testserver'))
    stamp=int(datetime.now(timezone.utc).timestamp())
    token=jwt.encode(dict(iss='fixture-issuer',aud='fixture-audience',sub=e.principal.principal_id,tid=e.tenant,jti=e.principal.token_id,rev=1,
        exp=stamp+600,iat=stamp,nbf=stamp-1),'fixture-key-'+'x'*64,algorithm='HS256')
    with TestClient(create_app(settings,e.service.registry),base_url='https://testserver') as client:
        client.app.state.tasks=e.service
        assert client.post('/api/v1/session',headers={'Authorization':'Bearer '+token}).status_code==200
        response=client.get(f'/api/v1/s01/v2/batches/{tid}/items/{item["entityKey"]}')
        assert response.status_code==200
        body=response.json();assert all(k in body for k in ['dataQuality','demandWindow','inventoryBasis','capabilities','recoveryHints'])
    assert e.service.read_report(e.principal,tid)==report and e.erp.mutations==0


def test_new_shipment_updates_stock_once_without_window_origin_coupling(make_s01,tmp_path,monkeypatch):
    import commerce_hub.data.sync.v2 as v2
    e=admitted_environment(make_s01,tmp_path,monkeypatch);first,original=run(e)
    new=deepcopy(e.erp.data['sales'][0]);new.update(id=99,order_time='2026-11-13 12:00:00');new['item_list'][0]['quantity']=3
    e.erp.data['sales'].append(new);e.erp.data['inventory'][0].update(quantity=3,available=3)
    event=deepcopy(e.erp.ledger[-1]);event.update(id=299,record_id=199,before_quantity=6,before_available=6,delta_quantity=-3,delta_available=-3,
        after_quantity=3,after_available=3,created_at='2026-11-13T06:30:00+00:00');e.erp.ledger.append(event)
    e.erp.workflows['99']=dict(data=dict(local_only=True,state='shipped',order_id=99,shipped_at=event['created_at'],shipments=[dict(order_id=99,outbound_id=199)]))
    monkeypatch.setattr(v2,'now',lambda:'2026-11-14T06:00:05+00:00')
    tid=e.service.create(e.principal,'new-shipment','S01_V2_BATCH',e.scope,{},'synthetic')['taskRef']['taskId'];assert Worker(e.service).once()
    with e.database.engine.connect() as c:item=next(iter(ItemStore.read(c,e.tenant,tid).values()))
    assert item['inventoryBasis']['status']=='VERIFIED' and item['inventoryBasis']['physical']=='3'
    assert item['demandWindow']['totalSales']=='38' and item['capabilities']['rules']['enabled']
    assert e.service.read_report(e.principal,first)==original
