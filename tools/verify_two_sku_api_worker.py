"""Two real read-only ERP singles through isolated G01/API/O01/Worker.

No full-catalog task, paid provider, ERP write adapter or existing-user mutation.
Temporary review principal is limited to an isolated local engineering tenant.
"""
import json,os,secrets
from pathlib import Path
from datetime import datetime,timezone,timedelta
from uuid import uuid4
from sqlalchemy import select,func
from pydantic import SecretStr
import jwt
from fastapi.testclient import TestClient
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.infrastructure.database import Database,assert_migration_target
from commerce_hub.governance.access import AccessControl
from commerce_hub.governance.observability.service import Audit
from commerce_hub.infrastructure.work import WorkStore
from commerce_hub.orchestration.service import TaskService,HandlerSpec
from commerce_hub.orchestration.worker import Worker
from commerce_hub.scenarios.s01_v2.handler import V2Handler,collection_scope
from commerce_hub.scenarios.s01_v2.policy import V2Policy
from commerce_hub.scenarios.s01_v2.store import ItemStore
from commerce_hub.data.projection.monitor import MonitorRegistry
from commerce_hub.data.sync.v2 import V2Reader
from commerce_hub.data.sync.v2_store import AcquisitionCheckpoint
from commerce_hub.bootstrap.s01_v2 import erp_config
from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.data.contracts import fingerprint

ROOT=Path(__file__).resolve().parents[1]


def main():
    if os.environ.get('S01_TWO_SKU_READONLY')!='1':raise SystemExit('Explicit S01_TWO_SKU_READONLY=1 required')
    s=load_settings();assert_migration_target(s);db=Database(s)
    tenant='two-sku-'+uuid4().hex;scope=collection_scope(tenant);key=secrets.token_urlsafe(64)
    access=AccessControl(db.engine,'two-sku-review','two-sku-review',key)
    with db.engine.begin() as c:
        now=c.scalar(select(func.utc_timestamp(6)))
        actor=access.provision_fixture(c,tenant_id=tenant,principal_id='readonly-review',token_id=uuid4().hex,
            expires_at=now+timedelta(hours=1),grants_by_action={a:scope for a in ['tasks:create','tasks:read','engineering:execute']})
    mappings=MonitorRegistry(db.engine,'s01-owned-teaching-local').mappings()
    mappings=[m for m in mappings if m.sku in {'HL-CBL100-2M','HL-MUG350-WH'}];assert len(mappings)==2
    policy=V2Policy(tenant,'1',owned_mappings=mappings,requisition_enabled=False)
    def reader(ctx):return V2Reader(erp_config(),ROOT/'data/private/two-sku-fix/api-worker'/ctx.task['task_id'],AcquisitionCheckpoint(ctx),ctx.check,request_limit=60,max_records=500)
    handler=V2Handler(db.engine,policy,reader,single=True,provider=None)
    batch=V2Handler(db.engine,policy,reader)
    registry={'S01_V2_SINGLE':HandlerSpec('S01_V2_SINGLE','0.1.0','two.sku.single.'+tenant,handler),
        'S01_V2_BATCH':HandlerSpec('S01_V2_BATCH','0.1.0','two.sku.batch.'+tenant,batch)}
    service=TaskService(db.engine,access,WorkStore(db.engine,lease_seconds=30),Audit(),registry,deadline_seconds=600)
    settings=s.model_copy(update=dict(environment='test',auth_issuer='two-sku-review',auth_audience='two-sku-review',auth_signing_key=SecretStr(key),browser_origin='https://testserver',local_admin_enabled=False))
    stamp=int(datetime.now(timezone.utc).timestamp())
    token=jwt.encode(dict(iss='two-sku-review',aud='two-sku-review',sub=actor.principal_id,tid=tenant,jti=actor.token_id,rev=1,exp=stamp+3600,iat=stamp,nbf=stamp-1),key,algorithm='HS256')
    old_tasks=['e8da93a39f264e74a6d2f2ebd700d9f5','2d3980e196094482b7ed1e6a48a45fa3']
    def original_digests():
        with db.engine.connect() as c:return {t:fingerprint(ItemStore.read(c,'s01-v2-teaching-local',t)) for t in old_tasks}
    before=original_digests();results=[]
    try:
        with TestClient(create_app(settings,registry),base_url='https://testserver') as client:
            client.app.state.tasks=service
            assert client.post('/api/v1/session',headers={'Authorization':'Bearer '+token}).status_code==200
            headers={'Origin':'https://testserver','X-CSRF-Token':client.cookies.get('commerce_csrf')}
            for m in mappings:
                e=dict(sourceTenant=m.sourceTenant,productId=m.monitor.productId,storeId=m.sourceStore,warehouseId=m.sourceWarehouse,sku=m.sku,storeName=m.storeName,warehouseName=m.warehouseName)
                e['entityKey']=fingerprint([m.sourceTenant,m.sourceStore,m.sourceWarehouse,m.monitor.productId,m.sku])
                reply=client.post('/api/v1/analysis-tasks',json=dict(analysisMode='SINGLE',scenarioId='S01_V2_SINGLE',scope={k:v for k,v in scope.items() if k!='tenantId'},parameters=dict(entity=e)),headers=dict(headers,**{'Idempotency-Key':uuid4().hex}))
                assert reply.status_code==202,reply.status_code
                tid=reply.json()['taskRef']['taskId'];assert Worker(service).once()
                response=client.get('/api/v1/s01/v2/singles/'+tid);assert response.status_code==200
                data=response.json();assert data['task']['state']=='SUCCEEDED'
                item=data['report']['dataReport']['item'];assert item['analysisState']=='HISTORICAL_REFERENCE' and item['quantity'] is None
                assert item['capabilities']['reference']['enabled'] and not item['procurementEligibility']['eligible']
                assert item['inventory']['available']==(6 if m.sku=='HL-CBL100-2M' else 81)
                results.append(dict(sku=m.sku,taskRef=dict(tenantId=tenant,taskId=tid),apiStatus=response.status_code,item=item))
                print(json.dumps(dict(sku=m.sku,state=item['analysisState'],inventory=item['inventory']['available'],validDays=item['demandWindow']['validDays'],referenceDays=item['demandWindow']['referenceDays'])),flush=True)
        assert before==original_digests()
        output=dict(nature='REAL_ERP_READONLY_THROUGH_REAL_MYSQL_API_AND_WORKER_ISOLATED_LOCAL_TENANT',results=results,oldUserReportsUnchanged=True,paidModels=0,erpBusinessWrites=0,fullCatalogTasks=0)
        p=ROOT/'docs/evidence/S01-TWO-SKU-FIX/api-worker.json';p.write_bytes((json.dumps(output,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    finally:db.close()


if __name__=='__main__':main()
