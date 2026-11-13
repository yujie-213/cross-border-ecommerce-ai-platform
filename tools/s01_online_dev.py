"""Controlled local online workbench. Explicit activation; no ERP writes.

Discover at most 20 inventory rows and 3 mappings, or reuse private mapping
metadata. Every new analysis still performs its own independent ERP collection.
This is a short-lived teaching identity, not a production identity service.
"""
import argparse
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import time
from uuid import uuid4
import hashlib
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PRIVATE=ROOT/'data/private/s01-online'

def alias(kind,value):return kind+'-'+hashlib.sha256(str(value).encode()).hexdigest()[:20]

def discover_mappings(tenant_id):
    from dotenv import dotenv_values
    from commerce_hub.adapters.erp import ERPConfig,TeachingERPReader
    v=dotenv_values(ROOT/'.env.erp',interpolate=False)
    reader=TeachingERPReader(ERPConfig(username=v.get('ERP_USERNAME') or '',password=v.get('ERP_PASSWORD') or '',
        access_token=v.get('ERP_ACCESS_TOKEN') or '',max_requests=8))
    stores=reader.discover('/api/v1/store-authorizations',page_size=20)
    if not stores.complete:raise ValueError('AUTHORIZED_STORE_LIST_INCOMPLETE')
    allowed={str(s['id']):s for s in stores.records}
    inventory=reader.discover('/api/v1/inventory',page_size=20)
    result=[];seen=set()
    for row in inventory.records:
        key=tuple(str(row.get(k)) for k in ('tenant_id','store_id','wid','sku'))
        if key in seen or str(row.get('store_id')) not in allowed:continue
        if not all(row.get(k) is not None for k in ('tenant_id','store_id','wid','sku','store_name','warehouse_name')):continue
        if allowed[str(row['store_id'])].get('tenant_id')!=row.get('tenant_id'):continue
        seen.add(key)
        result.append(dict(scope=dict(tenantId=tenant_id,storeIds=[alias('store',row['store_id'])],
            warehouseIds=[alias('warehouse',row['wid'])],canonicalSkuIds=[alias('sku',row['sku'])],fields=['quantity']),
            sku=row['sku'],sourceTenant=str(row['tenant_id']),sourceStore=str(row['store_id']),sourceWarehouse=str(row['wid']),
            storeName=row['store_name'],warehouseName=row['warehouse_name'],version='s01-online-map-v1',sourceSynthetic=True))
        if len(result)==3:break
    if not result:raise ValueError('NO_BOUNDED_AUTHORIZED_MAPPING')
    return result,dict(candidateLimit=20,selectedCount=len(result),inventoryEnumerationComplete=inventory.complete,
        sourceNature='TEACHING_ERP_OBSERVED',businessAdmission='BLOCKED',networkRequests=len(reader.events))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-local',action='store_true')
    parser.add_argument('--discover-options',action='store_true')
    parser.add_argument('--mapping',type=Path)
    parser.add_argument('--enable-model',action='store_true')
    parser.add_argument('--owned-monitor',action='store_true',help='Use only the durable ACTIVE owned registry')
    parser.add_argument('--enable-requisition',action='store_true',help='Explicit authorized teaching create/submit only; requires owned-monitor')
    parser.add_argument('--duration',type=int,choices=range(60,901),default=900)
    args=parser.parse_args()
    if not args.execute_local:
        print('NOT_RUN: explicit --execute-local required; no ERP/model IO');return
    if sum([bool(args.mapping), bool(args.discover_options), args.owned_monitor]) != 1:
        raise ValueError('SELECT_OWNED_MONITOR_OR_EXPLICIT_DIAGNOSTIC_SOURCE')
    if args.enable_requisition and (not args.owned_monitor or args.enable_model):
        raise ValueError('REQUISITION_REQUIRES_OWNED_SCOPE_AND_NO_NEW_MODEL_CALLS')
    os.environ['COMMERCE_S01_REQUISITION_ENABLED'] = 'true' if args.enable_requisition else 'false'
    os.environ.update(COMMERCE_ENVIRONMENT='test',COMMERCE_MODEL_PROVIDER='mock',COMMERCE_MODEL_NETWORK_ENABLED='false',
        COMMERCE_S01_ONLINE_EXPLANATION_MODE='off')
    if args.enable_model:
        os.environ.update(COMMERCE_MODEL_PROVIDER='deepseek',COMMERCE_MODEL_NETWORK_ENABLED='true',
            COMMERCE_MODEL_MAX_OUTPUT_TOKENS='1024',COMMERCE_MODEL_MAX_CONCURRENT='1',COMMERCE_MODEL_TIMEOUT_SECONDS='30',
            COMMERCE_S01_ONLINE_EXPLANATION_MODE='deepseek',COMMERCE_S01_ONLINE_AUTHORIZATION='s01-mvp-20261113-p1p2' if args.owned_monitor else 's01-online-20261113-r1')
    import jwt
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database,assert_migration_target
    from commerce_hub.governance.access import AccessControl
    from tests.support.s01_process import S01ProcessHarness
    from commerce_hub.data.sync.online import OnlineMapping
    settings=load_settings();assert_migration_target(settings);database=Database(settings)
    if not database.schema_ready():
        database.close();raise ValueError('EXPLICIT_MIGRATION_REQUIRED_BEFORE_STARTUP')
    harness=S01ProcessHarness(database,settings)
    harness.tenant='s01-owned-teaching-local' if args.owned_monitor else 's01-online-teaching-local'
    try:
        if args.owned_monitor:
            from commerce_hub.data.projection.monitor import MonitorRegistry
            mappings=[m.model_dump(mode='json') for m in MonitorRegistry(database.engine,harness.tenant).mappings()]
            discovery=dict(mode='ACTIVE_OWNED_MONITOR_REGISTRY',networkRequests=0)
        elif args.discover_options:
            mappings,discovery=discover_mappings(harness.tenant)
        else:
            path=args.mapping.resolve()
            if not path.is_relative_to(PRIVATE.resolve()):raise ValueError('PRIVATE_ONLINE_MAPPING_REQUIRED')
            mappings=json.loads(path.read_text(encoding='utf-8'))
            mappings=[dict(m,scope=dict(m['scope'],tenantId=harness.tenant)) for m in mappings]
            discovery=dict(mode='REUSED_MAPPING_METADATA_ONLY',networkRequests=0)
        mappings=[OnlineMapping.model_validate(m).validate_scope().model_dump(mode='json') for m in mappings]
        if not 1<=len(mappings)<=20:raise ValueError('ONLINE_MAPPING_LIMIT')
        scope=dict(tenantId=harness.tenant,fields=['quantity'],**{k:sorted({v for m in mappings for v in m['scope'][k]})
            for k in ('storeIds','warehouseIds','canonicalSkuIds')})
        now=datetime.now(timezone.utc);harness.principal_id='online-'+uuid4().hex[:20];harness.token_id=uuid4().hex
        access=AccessControl(database.engine,harness.issuer,harness.audience,harness.key)
        with database.engine.begin() as conn:
            access.provision_fixture(conn,tenant_id=harness.tenant,principal_id=harness.principal_id,token_id=harness.token_id,
                expires_at=now+timedelta(seconds=args.duration),grants_by_action={a:scope for a in
                    ['tasks:create','tasks:read','tasks:cancel','engineering:execute'] + (['s01:requisition'] if args.enable_requisition else [])})
        harness.token=jwt.encode(dict(iss=harness.issuer,aud=harness.audience,exp=int(now.timestamp())+args.duration,
            iat=int(now.timestamp()),nbf=int(now.timestamp())-1,sub=harness.principal_id,tid=harness.tenant,jti=harness.token_id,rev=1),harness.key,algorithm='HS256')
        harness.secrets.append(harness.token)
        run_dir=PRIVATE/('local-'+uuid4().hex);run_dir.mkdir(parents=True)
        path=run_dir/'mapping.json';path.write_text(json.dumps(mappings,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
        (run_dir/'discovery.json').write_text(json.dumps(discovery,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
        harness.module='commerce_hub.bootstrap.s01_online'
        harness.environment.update(os.environ)
        # Restore the owned short-lived G01 assembly after inherited settings.
        harness.environment.update(COMMERCE_AUTH_ISSUER=harness.issuer,COMMERCE_AUTH_AUDIENCE=harness.audience,
            COMMERCE_AUTH_SIGNING_KEY=harness.key,COMMERCE_S01_ONLINE_ENABLED='true',COMMERCE_S01_ONLINE_MAPPING_PATH=str(path),
            COMMERCE_LEASE_SECONDS='10',COMMERCE_HEARTBEAT_SECONDS='1',COMMERCE_TASK_DEADLINE_SECONDS='240',COMMERCE_BROWSER_ORIGIN='http://localhost:5173')
        if args.owned_monitor:
            harness.environment.update(COMMERCE_S01_OWNED_MONITORING='true',COMMERCE_S01_MONITOR_TENANT=harness.tenant)
        harness.start_api();worker=harness.start_worker()
        receipt=dict(apiTarget=str(harness.client.base_url).rstrip('/'),token=harness.token,
            expiresAt=(now+timedelta(seconds=args.duration)).isoformat(),mappingPath=str(path),
            tenantId=harness.tenant,principalId=harness.principal_id,tokenId=harness.token_id,
            apiPid=harness.api.process.pid,workerPid=worker.process.pid,modelAuthorization=os.environ.get('COMMERCE_S01_ONLINE_AUTHORIZATION') if args.enable_model else None,
            monitoring='ACTIVE_OWNED_REGISTRY' if args.owned_monitor else 'DIAGNOSTIC_ONLY')
        (PRIVATE/'session.json').write_text(json.dumps(receipt),encoding='utf-8',newline='\n')
        print('READY: online API/Worker, bounded authorized choices, private short-lived session written',flush=True)
        until=time.monotonic()+args.duration
        control_path = PRIVATE / 'owned-test-control.json'
        if args.owned_monitor: control_path.write_text('{"status":"IDLE"}',encoding='utf-8')
        while time.monotonic()<until:
            if args.owned_monitor and control_path.exists():
                command=json.loads(control_path.read_text(encoding='utf-8'))
                if command.get('status')=='REQUESTED':
                    action=command.get('action')
                    if action=='pauseWorker':worker.stop()
                    elif action=='resumeWorker':
                        if worker.process.poll() is not None:worker=harness.start_worker()
                    elif action=='restartProcesses':
                        worker.stop();harness.api.stop();harness.start_api();worker=harness.start_worker()
                        receipt.update(apiTarget=str(harness.client.base_url).rstrip('/'),apiPid=harness.api.process.pid,workerPid=worker.process.pid)
                        (PRIVATE/'session.json').write_text(json.dumps(receipt),encoding='utf-8')
                    else:raise ValueError('UNKNOWN_LOCAL_TEST_CONTROL')
                    control_path.write_text(json.dumps(dict(command,status='DONE')),encoding='utf-8')
            time.sleep(.2)
    finally:harness.close();database.close()

if __name__=='__main__':main()
