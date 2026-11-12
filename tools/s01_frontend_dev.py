"""Controlled local browser integration: existing G01 fixture, fixed teaching GET captures.

No ERP/model network; no anonymous identity endpoint; private short-lived bearer receipt.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-local', action='store_true')
    parser.add_argument('--catalog', default='data/private/s01-teaching-dataset/S01-AI-TEST-20261112/catalog.json')
    parser.add_argument('--duration', type=int, choices=range(60, 901), default=900)
    args = parser.parse_args()
    if not args.execute_local:
        print('NOT_RUN: explicit --execute-local required; no ERP/model IO')
        return
    os.environ.update(COMMERCE_ENVIRONMENT='test', COMMERCE_MODEL_PROVIDER='mock', COMMERCE_MODEL_NETWORK_ENABLED='false')
    import jwt
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.governance.access import AccessControl
    from commerce_hub.infrastructure.database import Database, assert_migration_target
    from tests.support.backend import BackendHarness

    settings = load_settings()
    assert_migration_target(settings)
    path = (ROOT / args.catalog).resolve()
    if not path.is_relative_to((ROOT / 'data/private').resolve()):
        raise SystemExit('PRIVATE_FIXED_CATALOG_REQUIRED')
    catalog = json.loads(path.read_text(encoding='utf-8'))
    entries = [{k: row[k] for k in ('kind', 'payload')} for row in catalog['entries']]
    if not entries or any(e['kind'] != 'TEACHING_SIMULATION' for e in entries):
        raise SystemExit('TEACHING_CAPTURE_CATALOG_REQUIRED')
    scope = entries[0]['payload']['scope']
    if any(e['payload']['scope'] != scope for e in entries):
        raise SystemExit('SINGLE_PRECISE_SCOPE_REQUIRED')
    # Existing authorized isolated database only. Never migrate, clear, or inspect other DBs.
    database = Database(settings)
    harness = BackendHarness(database, settings, entries, mock=False)
    try:
        harness.tenant, harness.scope = scope['tenantId'], scope
        harness.principal_id = 's01-ui-' + uuid4().hex[:20]
        now = datetime.now(timezone.utc)
        access = AccessControl(database.engine, harness.issuer, harness.audience, harness.key)
        with database.engine.begin() as conn:
            access.provision_fixture(conn, tenant_id=harness.tenant, principal_id=harness.principal_id,
                token_id=harness.token_id, expires_at=now + timedelta(seconds=args.duration),
                grants_by_action={a: scope for a in ['tasks:create', 'tasks:read', 'tasks:cancel', 'engineering:execute']})
        harness.token = jwt.encode(dict(iss=harness.issuer, aud=harness.audience, exp=int(now.timestamp()) + args.duration,
            iat=int(now.timestamp()), nbf=int(now.timestamp()) - 1, sub=harness.principal_id,
            tid=harness.tenant, jti=harness.token_id, rev=1), harness.key, algorithm='HS256')
        harness.secrets.append(harness.token)
        harness.environment.update(COMMERCE_BROWSER_ORIGIN='http://localhost:5173',
            COMMERCE_TASK_DEADLINE_SECONDS='120', COMMERCE_MAX_DELIVERY_ATTEMPTS='1')
        harness.start_api()
        worker = harness.start_worker()
        private = ROOT / 'data/private/s01-frontend'
        private.mkdir(parents=True, exist_ok=True)
        (private / 'control.json').write_text('{"status":"IDLE"}', encoding='utf-8')
        receipt = dict(apiTarget=str(harness.client.base_url).rstrip('/'), token=harness.token,
            expiresAt=(now + timedelta(seconds=args.duration)).isoformat(), apiPid=harness.api.process.pid,
            workerPid=worker.process.pid, principalId=harness.principal_id, tenantId=harness.tenant,
            tokenId=harness.token_id, casePackages=[dict(caseId=r['caseId'], packageRef=__import__('commerce_hub.scenarios.s01_backend', fromlist=['package_ref']).package_ref(r['kind'], r['payload'])) for r in catalog['entries']])
        (private / 'session.json').write_text(json.dumps(receipt), encoding='utf-8')
        print('READY: independent API/Worker, authorized isolated MySQL, off mode; private session receipt written', flush=True)
        # Owned process persists only for the bounded local demonstration window.
        until = time.monotonic() + args.duration
        while time.monotonic() < until:
            # Test-only local file control; never registered as an HTTP capability.
            command_path = private / 'control.json'
            if command_path.exists():
                try:
                    command = json.loads(command_path.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    time.sleep(.2)
                    continue
                if command.get('status') == 'REQUESTED':
                    action = command.get('action')
                    if action == 'pauseWorker':
                        worker.stop()
                    elif action == 'resumeWorker':
                        if worker.process.poll() is not None:
                            worker = harness.start_worker()
                    elif action in {'revokeRead', 'restoreRead'}:
                        from sqlalchemy import update
                        from commerce_hub.governance.access.tables import grants
                        with database.engine.begin() as conn:
                            conn.execute(update(grants).where(grants.c.tenant_id == harness.tenant,
                                grants.c.principal_id == harness.principal_id,
                                grants.c.action == 'tasks:read').values(scope=scope if action == 'restoreRead' else dict(scope, fields=['outside'])))
                    else:
                        raise ValueError('UNKNOWN_LOCAL_TEST_CONTROL')
                    command_path.write_text(json.dumps(dict(command, status='DONE')), encoding='utf-8')
            time.sleep(.2)
    finally:
        harness.close()
        database.close()


if __name__ == '__main__':
    main()
