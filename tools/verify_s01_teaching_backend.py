"""Actual private GET packages through independent API/Worker/MySQL; no network ERP/model IO."""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
os.environ.update(COMMERCE_ENVIRONMENT='test', COMMERCE_MODEL_PROVIDER='mock', COMMERCE_MODEL_NETWORK_ENABLED='false')
import jwt
from sqlalchemy import select, text, update
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.governance.access import AccessControl
from commerce_hub.governance.access.tables import grants
from commerce_hub.infrastructure.database import Database, assert_migration_target
from commerce_hub.orchestration.tables import tasks, reports
from tests.support.backend import BackendHarness

settings = load_settings()
assert_migration_target(settings)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('catalog_path', help='Final fixed catalog under data/private/')
args = parser.parse_args()
catalog_path = Path(args.catalog_path).resolve()
assert catalog_path.is_relative_to((ROOT / 'data/private').resolve())
catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
entries = [{k: row[k] for k in ('kind', 'payload')} for row in catalog['entries']]
scope = entries[0]['payload']['scope']
database = Database(settings)
h = BackendHarness(database, settings, entries, mock=False)
try:
    h.tenant, h.scope = scope['tenantId'], scope
    h.principal_id = 's01-teaching-e2e-' + uuid4().hex[:20]
    control = AccessControl(database.engine,h.issuer,h.audience,h.key)
    now = datetime.now(timezone.utc)
    with database.engine.begin() as connection:
        control.provision_fixture(connection,tenant_id=h.tenant,principal_id=h.principal_id,token_id=h.token_id,
            expires_at=now+timedelta(minutes=15), grants_by_action={a:scope for a in
                ['tasks:create','tasks:read','tasks:cancel','engineering:execute']})
    h.token = jwt.encode(dict(iss=h.issuer,aud=h.audience,exp=int(now.timestamp())+900,
        iat=int(now.timestamp()),nbf=int(now.timestamp())-1,sub=h.principal_id,tid=h.tenant,jti=h.token_id,rev=1),h.key,algorithm='HS256')
    h.environment.update(COMMERCE_TASK_DEADLINE_SECONDS='120',COMMERCE_MAX_DELIVERY_ATTEMPTS='1')
    h.start_api()
    options = h.client.get('/api/v1/s01/options')
    assert options.status_code==200 and len(options.json()['mappedChoices'])==5
    worker = h.start_worker()
    result_rows, private_rows = [], []
    previous = None
    for case, entry in zip(catalog['entries'],entries):
        created, body, key = h.submit(entry=entry,previous=previous if case['caseId']=='B' else None)
        task_id = created['taskRef']['taskId']
        h.wait_state(task_id,'SUCCEEDED')
        report = h.report(task_id)
        assert report['sourceNature']=='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'
        assert report['analysisReport']['ai']['status']=='NOT_ATTEMPTED'
        assert report['dataReport']['scenarioSupplement']['procurementEligible'] is False
        assert report['dataReport']['scenarioSupplement']['realAdmission']=='BLOCKED'
        assert not {'sourcePackage','inputProjection','manifest'} & set(report['dataReport'])
        replay=h.client.post('/api/v1/analysis-tasks',json=body,headers={'Idempotency-Key':key})
        assert replay.status_code==202 and replay.json()['reportRef']==report['reportRef']
        for ev in report['dataReport']['evidence']:
            assert h.client.get(f'/api/v1/analysis-tasks/{task_id}/evidence/{ev["evidenceId"]}').status_code==200
        budget=h.budget(task_id)
        assert budget['used_calls']==budget['reserved_calls']==0
        supply=report['dataReport']['supplyDemand']
        baseline=supply['baseline']
        if case['caseId']=='A':
            assert baseline['gapQuantity']=='17' and supply['candidates'][0]['quantity']=='18'
            assert supply['candidates'][0]['evaluation']['stockoutRisk'] is True
            previous=report['reportRef']
        elif case['caseId']=='B':
            assert baseline['gapQuantity']=='0' and not supply['candidates']
            assert report['dataReport']['scenarioSupplement']['previousReportRef']==previous
        elif case['caseId']=='C':
            assert baseline['gapQuantity']=='0' and baseline['stockoutRisk'] is True and not supply['candidates']
        else:
            assert not supply['candidates']
        result_rows.append(dict(caseId=case['caseId'],taskRef=report['taskRef'],reportRef=report['reportRef'],
            snapshotRef=report['snapshotRef'],state='SUCCEEDED',completeness=report['completeness'],
            sourceNature=report['sourceNature'],aiStatus='NOT_ATTEMPTED',gapQuantity=baseline['gapQuantity'] if baseline else None,
            candidateCount=len(supply['candidates']),limitations=supply['limitations'],
            qualityCodes=[i['code'] for i in report['dataReport']['quality']],
            evidenceCount=len(report['dataReport']['evidence']),idempotency='PASS',procurementEligible=False))
        private_rows.append(dict(caseId=case['caseId'],body=body,commandKey=key,report=report))
    last_id=result_rows[-1]['taskRef']['taskId']
    h.api.stop(); h.start_api()
    assert h.report(last_id)==private_rows[-1]['report']
    history=h.client.get('/api/v1/analysis-tasks',params=dict(storeId=scope['storeIds'][0],
        warehouseId=scope['warehouseIds'][0],canonicalSkuId=scope['canonicalSkuIds'][0],scenarioId='S01_BACKEND',limit=50))
    assert history.status_code==200
    ids={x['taskRef']['taskId'] for x in history.json()['items']}
    assert all(r['taskRef']['taskId'] in ids for r in result_rows)
    with database.engine.begin() as connection:
        meta=connection.execute(text('SELECT VERSION(),DATABASE(),@@session.time_zone,@@transaction_isolation')).one()
        connection.execute(update(grants).where(grants.c.tenant_id==h.tenant,grants.c.principal_id==h.principal_id)
            .values(scope=dict(scope,fields=['outside'])))
    assert h.client.get('/api/v1/s01/options').json()['mappedChoices']==[]
    assert h.client.get('/api/v1/analysis-tasks/'+last_id+'/report').status_code==404
    private_path=catalog_path.parent/('backend-process-'+uuid4().hex+'.json')
    private_path.write_text(json.dumps(private_rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    output=dict(schemaVersion='s01-teaching-backend-process-v1',result='PASS',capturedAt=datetime.now(timezone.utc).isoformat(),
        observedImplementationCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        command='python -m tools.verify_s01_teaching_backend <private-catalog>',
        inputKind='FIXED_REAL_GET_CAPTURE_OF_SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',
        erpNetworkRequestsThisRun=0,realModelRequests=0,procurementWrites=0,
        processes=dict(apiPid=h.api.process.pid,workerPid=worker.process.pid,independent=True,apiRestarted=True),
        database=dict(server=meta[0],name=meta[1],timeZone=meta[2],isolation=meta[3],cleared=False),cases=result_rows,
        verification=dict(options=True,history=True,reportPersistenceAcrossRestart=True,idempotency=True,
            previousReportRelation=True,currentPermissionRevocation=True,internalAssetsCropped=True,evidenceResolution=True),
        privateArtifactSha256=hashlib.sha256(private_path.read_bytes()).hexdigest(),
        enterpriseAdmission='BLOCKED',frontend='NOT_RUN')
    path=ROOT/'docs/evidence/S01-BACKEND/teaching-data/backend-process.json'
    path.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result='PASS',cases=5,sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',
                         realModelRequests=0,enterpriseAdmission='BLOCKED')))
finally:
    h.close()
    database.close()
