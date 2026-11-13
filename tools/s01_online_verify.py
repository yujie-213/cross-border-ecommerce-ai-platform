"""Explicit live ERP/API/Worker checks. Default is NOT_RUN; never calls a model."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import time
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]

def live_mapping(scope):
    # Source identity metadata only. No catalog quantities, demand or package facts.
    probe=json.loads((ROOT/'data/private/s01-online-20261113/probe.json').read_text(encoding='utf-8'))
    row=probe['inventory']['rows'][0]
    return dict(scope=scope,sku=row['sku'],sourceTenant=str(row['tenant_id']),sourceStore=str(row['store_id']),
        sourceWarehouse=str(row['wid']),storeName=row['store_name'],warehouseName=row['warehouse_name'],
        teachingReplay=True,sourceSynthetic=True,version='s01-online-map-v1')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-live',action='store_true')
    parser.add_argument('--serve',action='store_true')
    parser.add_argument('--duration',type=int,default=600,choices=range(60,901))
    args=parser.parse_args()
    if not args.execute_live:
        print('NOT_RUN: explicit --execute-live required; no ERP/model IO');return
    os.environ.update(COMMERCE_ENVIRONMENT='test',COMMERCE_MODEL_PROVIDER='mock',COMMERCE_MODEL_NETWORK_ENABLED='false')
    from sqlalchemy import select
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database,migrate
    from commerce_hub.data.sync.online_store import acquisitions
    from commerce_hub.data.quality.online_store import snapshots
    from tests.support.s01_process import S01ProcessHarness
    settings=load_settings();migrate(settings);db=Database(settings)
    harness=S01ProcessHarness(db,settings)
    private=ROOT/'data/private/s01-online-20261113'/('run-'+uuid4().hex)
    private.mkdir(parents=True)
    mapped=live_mapping(harness.scope)
    path=private/'mapping.json';path.write_text(json.dumps([mapped],ensure_ascii=False),encoding='utf-8')
    harness.module='commerce_hub.bootstrap.s01_online'
    harness.environment.update(COMMERCE_S01_ONLINE_ENABLED='true',COMMERCE_S01_ONLINE_MAPPING_PATH=str(path),
        COMMERCE_TASK_DEADLINE_SECONDS='240',COMMERCE_LEASE_SECONDS='10',COMMERCE_HEARTBEAT_SECONDS='1',
        COMMERCE_BROWSER_ORIGIN='http://localhost:5173')
    evidence=dict(testedCommit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        capturedAt=datetime.now(timezone.utc).isoformat(),kind='REAL_ERP_REAL_MYSQL_API_INDEPENDENT_WORKER',models='NOT_RUN',tasks=[])
    try:
        harness.start_api();worker=harness.start_worker()
        receipt=dict(apiTarget=str(harness.client.base_url).rstrip('/'),token=harness.token,
            tenantId=harness.tenant,principalId=harness.principal_id,tokenId=harness.token_id,
            apiPid=harness.api.process.pid,workerPid=worker.process.pid,mappingPath=str(path),privateRun=str(private))
        (ROOT/'data/private/s01-online-20261113/session.json').write_text(json.dumps(receipt),encoding='utf-8')
        if args.serve:
            print('READY: online API/Worker; private session receipt written',flush=True)
            time.sleep(args.duration);return
        for index in range(2):
            key=uuid4().hex
            body=dict(analysisMode='SINGLE',scenarioId='S01_BACKEND',scope={k:v for k,v in harness.scope.items() if k!='tenantId'},parameters=dict(inputMode='ONLINE_TEACHING_ERP'),previousReportRef=None)
            accepted=harness.client.post('/api/v1/analysis-tasks',json=body,headers={'Idempotency-Key':key});assert accepted.status_code==202
            tid=accepted.json()['taskRef']['taskId']
            until=time.monotonic()+220
            while time.monotonic()<until:
                task=harness.client.get('/api/v1/analysis-tasks/'+tid).json()
                if task['state'] in {'SUCCEEDED','FAILED','CANCELLED'}:break
                time.sleep(.5)
            assert task['state']=='SUCCEEDED',task.get('errorCode')
            report=harness.report(tid)
            replay=harness.client.post('/api/v1/analysis-tasks',json=body,headers={'Idempotency-Key':key})
            assert replay.json()['taskRef']['taskId']==tid
            with db.engine.connect() as conn:
                rows=conn.execute(select(acquisitions).filter_by(tenant_id=harness.tenant,task_id=tid)).mappings().all()
                stored=conn.execute(select(snapshots).filter_by(tenant_id=harness.tenant,task_id=tid)).mappings().one()
            assert len(rows)==1 and rows[0]['state']=='CAPTURED' and stored['snapshot_id']==report['snapshotRef']
            evidence['tasks'].append(dict(taskId=tid,state=task['state'],snapshotRef=report['snapshotRef'],
                acquisition=report['dataReport']['acquisition'],completeness=report['completeness'],
                calculation=report['dataReport']['supplyDemand'],quality=report['dataReport']['quality'],
                ai=report['analysisReport']['ai'],idempotentReplay='PASS',immutableSnapshot='PASS'))
            print('LIVE_TASK',index+1,task['state'],report['completeness'],flush=True)
        assert evidence['tasks'][0]['snapshotRef']!=evidence['tasks'][1]['snapshotRef']
        first=evidence['tasks'][0];before=harness.report(first['taskId'])
        harness.api.stop();harness.start_api();worker.stop();harness.start_worker()
        assert before==harness.report(first['taskId'])
        evidence.update(result='PASS',independentAcquisitions='PASS',apiWorkerRestartHistoricalRead='PASS')
        target=ROOT/'docs/evidence/S01-ONLINE/phase1-live.json';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
        print('PASS: two independent live collections, replay, immutable snapshots and restart read',flush=True)
    finally:
        harness.close();db.close()

if __name__=='__main__':main()
