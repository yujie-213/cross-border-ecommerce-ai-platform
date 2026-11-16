"""Real HTTP, independent Worker/restart, MySQL and compiled Vue engineering E2E."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import update,select

from tests.integration.after_sales.test_workflows import env,mutate,read
from tests.integration.processes.test_foundation_processes import OwnedProcess
from commerce_hub.governance.access.tables import grants
from commerce_hub.scenarios.s01_v2.handler import collection_scope
from commerce_hub.scenarios.after_sales.teaching import golden_package
from commerce_hub.orchestration.tables import budgets


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));return sock.getsockname()[1]


@pytest.mark.mysql
def test_independent_worker_crash_api_restart_and_actual_vue_product(env,tmp_path):
    e=env;api_port,web_port=free_port(),free_port()
    root=Path(__file__).resolve().parents[3]
    environment=dict(os.environ,COMMERCE_ENVIRONMENT='test',COMMERCE_B_ENABLED='true',
        B_WORKFLOW_TEST_TENANT=e.actor.tenant_id,COMMERCE_S01_V2_APP_TENANT=e.actor.tenant_id,
        COMMERCE_LOCAL_ADMIN_ENABLED='true',COMMERCE_AUTH_ISSUER='b-test',COMMERCE_AUTH_AUDIENCE='b-test',
        COMMERCE_AUTH_SIGNING_KEY=e.settings.auth_signing_key.get_secret_value(),
        COMMERCE_BROWSER_ORIGIN=f'http://localhost:{web_port}',COMMERCE_LOCAL_API_PORT=str(api_port),
        COMMERCE_LEASE_SECONDS='1',COMMERCE_HEARTBEAT_SECONDS='.15',COMMERCE_POLL_SECONDS='.05',
        COMMERCE_MODEL_PROVIDER='mock',COMMERCE_MODEL_NETWORK_ENABLED='false')
    with e.database.engine.begin() as conn:
        conn.execute(update(grants).filter_by(tenant_id=e.actor.tenant_id).values(scope=collection_scope(e.actor.tenant_id)))
    m,blocks=golden_package();m['datasetId']='process-recovery-'+uuid4().hex
    d=e.domain.create_dataset(e.actor,uuid4().hex,dict(manifest=m))
    for i,b in enumerate(blocks):d=e.domain.upload(e.actor,d['id'],uuid4().hex,i,b,d['revision'])
    mutate(e,'DATASET',d['id'],'seal')
    d=read(e,'DATASET',d['id'])
    task=e.domain.job(e.actor,'DATASET',d['id'],'validate',uuid4().hex,d['revision'],{})
    tid=task['taskRef']['taskId']
    processes=[]
    client=httpx.Client(base_url=f'http://127.0.0.1:{api_port}',cookies={'commerce_session':e.token},timeout=4,trust_env=False)
    def launch(args,extra=None):
        p=OwnedProcess(args,dict(environment,**(extra or {})));processes.append(p);return p
    def ready(url):
        stop=time.monotonic()+15
        while time.monotonic()<stop:
            try:
                if httpx.get(url,trust_env=False,timeout=1).status_code==200:return
            except httpx.TransportError:pass
            time.sleep(.1)
        pytest.fail('Owned engineering service readiness timeout')
    def api():
        p=launch([sys.executable,'-m','uvicorn','tests.support.b_workflows:create_app','--factory','--host','127.0.0.1','--port',str(api_port),'--no-access-log'])
        ready(f'http://127.0.0.1:{api_port}/health/ready');return p
    def state(wanted):
        stop=time.monotonic()+20
        while time.monotonic()<stop:
            response=client.get('/api/v1/analysis-tasks/'+tid)
            assert response.status_code==200
            if response.json()['state']==wanted:return response.json()
            time.sleep(.1)
        pytest.fail('Owned production B task failed to reach '+wanted)
    try:
        server=api();state('QUEUED');server.stop();api();state('QUEUED')
        with e.database.engine.connect() as conn:before=dict(conn.execute(select(budgets).filter_by(tenant_id=e.actor.tenant_id,task_id=tid)).mappings().one())
        worker=launch([sys.executable,'-m','tests.support.b_workflows','worker'],{'B_WORKFLOW_TEST_DELAY':'2'})
        state('RUNNING');worker.stop(crash=True)
        launch([sys.executable,'-m','tests.support.b_workflows','worker'])
        assert state('SUCCEEDED')['deadline']==task['deadline']
        assert read(e,'DATASET',d['id'])['state']=='READBACK_VERIFIED'
        with e.database.engine.connect() as conn:assert dict(conn.execute(select(budgets).filter_by(tenant_id=e.actor.tenant_id,task_id=tid)).mappings().one())==before
        launch([sys.executable,'-m','uvicorn','commerce_hub.entrypoints.http.local_frontend:create_app','--factory','--host','127.0.0.1','--port',str(web_port),'--no-access-log'])
        ready(f'http://localhost:{web_port}/health/frontend')
        browser_env=dict(environment,B_BROWSER_URL=f'http://localhost:{web_port}',B_BROWSER_PASSWORD='synthetic-only-password')
        node=shutil.which('node.exe') or shutil.which('node')
        assert node,'Node runtime required for actual Vue E2E'
        result=subprocess.run([node,'node_modules/@playwright/test/cli.js','test','--config=../tests/browser/after-sales/playwright.config.ts'],
            cwd=root/'frontend',env=browser_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
        (root/'.tmp/b-browser-command.log').write_bytes(result.stdout)
        assert result.returncode==0,'Vue browser E2E failed; inspect .tmp/b-browser-command.log'
    finally:
        client.close()
        for p in reversed(processes):p.stop()
        for p in processes:
            output=b''.join(p.lines).decode('utf-8',errors='replace')
            assert e.token not in output and e.settings.db_password.get_secret_value() not in output
