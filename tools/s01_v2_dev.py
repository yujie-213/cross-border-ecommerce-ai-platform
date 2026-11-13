"""Explicit short-lived teaching V2 API/Worker session; no source IO on startup."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import argparse,json,os,sys,time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
PRIVATE=ROOT/'data/private/s01-v2-local'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-local',action='store_true')
    parser.add_argument('--enable-model',action='store_true')
    parser.add_argument('--enable-requisition',action='store_true')
    parser.add_argument('--duration',type=int,default=900,choices=range(60,3601))
    args=parser.parse_args()
    if not args.execute_local:print('NOT_RUN: explicit activation required');return
    os.environ.update(COMMERCE_ENVIRONMENT='test',COMMERCE_MODEL_PROVIDER='deepseek' if args.enable_model else 'mock',
        COMMERCE_MODEL_NETWORK_ENABLED='true' if args.enable_model else 'false',COMMERCE_MODEL_MAX_OUTPUT_TOKENS='1024',
        COMMERCE_MODEL_MAX_CONCURRENT='1',COMMERCE_MODEL_TIMEOUT_SECONDS='30',COMMERCE_S01_V2_ENABLED='true',
        COMMERCE_S01_V2_MODEL_ENABLED='true' if args.enable_model else 'false',
        COMMERCE_S01_V2_REQUISITION_ENABLED='true' if args.enable_requisition else 'false',
        COMMERCE_S01_V2_APP_TENANT='s01-v2-teaching-local',COMMERCE_S01_V2_SOURCE_TENANT='1',
        COMMERCE_TASK_DEADLINE_SECONDS='600',COMMERCE_MAX_DELIVERY_ATTEMPTS='3')
    import jwt
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database,assert_migration_target
    from commerce_hub.governance.access import AccessControl
    from commerce_hub.scenarios.s01_v2.handler import collection_scope
    from tests.support.s01_process import S01ProcessHarness
    settings=load_settings();assert_migration_target(settings);db=Database(settings)
    if not db.schema_ready():db.close();raise ValueError('EXPLICIT_MIGRATION_REQUIRED')
    h=S01ProcessHarness(db,settings);h.module='commerce_hub.bootstrap.s01_v2';h.tenant='s01-v2-teaching-local'
    h.principal_id='v2-local-'+uuid4().hex[:20];h.token_id=uuid4().hex;scope=collection_scope(h.tenant)
    access=AccessControl(db.engine,h.issuer,h.audience,h.key);now=datetime.now(timezone.utc)
    try:
        with db.engine.begin() as c:access.provision_fixture(c,tenant_id=h.tenant,principal_id=h.principal_id,token_id=h.token_id,
            expires_at=now+timedelta(seconds=args.duration),grants_by_action={a:scope for a in
                ['tasks:create','tasks:read','tasks:cancel','engineering:execute']+(['s01:requisition'] if args.enable_requisition else [])})
        h.token=jwt.encode(dict(iss=h.issuer,aud=h.audience,sub=h.principal_id,tid=h.tenant,jti=h.token_id,rev=1,
            exp=int(now.timestamp())+args.duration,iat=int(now.timestamp()),nbf=int(now.timestamp())-1),h.key,algorithm='HS256')
        h.secrets.append(h.token);h.environment.update(os.environ)
        h.environment.update(COMMERCE_AUTH_ISSUER=h.issuer,COMMERCE_AUTH_AUDIENCE=h.audience,COMMERCE_AUTH_SIGNING_KEY=h.key,
            COMMERCE_LEASE_SECONDS='10',COMMERCE_HEARTBEAT_SECONDS='1',COMMERCE_BROWSER_ORIGIN='http://localhost:5173')
        h.start_api();worker=h.start_worker();PRIVATE.mkdir(parents=True,exist_ok=True)
        receipt=dict(apiTarget=str(h.client.base_url).rstrip('/'),token=h.token,expiresAt=(now+timedelta(seconds=args.duration)).isoformat(),
            principalId=h.principal_id,tenantId=h.tenant,apiPid=h.api.process.pid,workerPid=worker.process.pid,modelEnabled=args.enable_model,requisitionEnabled=args.enable_requisition)
        (PRIVATE/'session.json').write_text(json.dumps(receipt),encoding='utf-8')
        control=PRIVATE/'control.json';control.write_text('{"status":"IDLE"}',encoding='utf-8')
        print('READY: V2 independent API/Worker; private trusted session written; no ERP/model calls on startup',flush=True)
        until=time.monotonic()+args.duration
        while time.monotonic()<until:
            command=json.loads(control.read_text(encoding='utf-8'))
            if command.get('status')=='REQUESTED':
                action=command.get('action')
                if action=='stop':break
                if action=='restart':
                    worker.stop();h.api.stop();h.start_api();worker=h.start_worker()
                    receipt.update(apiTarget=str(h.client.base_url).rstrip('/'),apiPid=h.api.process.pid,workerPid=worker.process.pid)
                    (PRIVATE/'session.json').write_text(json.dumps(receipt),encoding='utf-8')
                elif action=='pauseWorker':worker.stop()
                elif action=='resumeWorker':
                    if worker.process.poll() is not None:worker=h.start_worker()
                else:raise ValueError('UNKNOWN_LOCAL_CONTROL')
                control.write_text(json.dumps(dict(command,status='DONE')),encoding='utf-8')
            time.sleep(.2)
    finally:h.close();db.close();print('STOPPED: owned API/Worker processes closed',flush=True)


if __name__=='__main__':main()
