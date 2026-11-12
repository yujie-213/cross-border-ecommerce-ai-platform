"""Fixed-commit backend regression for the S01 UI delivery; never rewrites old evidence."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-backend', action='store_true')
    parser.add_argument('--evidence-dir', default='docs/evidence/D-S01-UI-01')
    parser.add_argument('--baseline-evidence', default='docs/evidence/S01-BACKEND/verification.json')
    args = parser.parse_args()
    if not args.run_backend:
        print('NOT_RUN: --run-backend requires authorized isolated MySQL; no ERP/model requests')
        return 0
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'diff', '--name-only', 'HEAD'], cwd=ROOT, text=True).splitlines()
    dirty += subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    if any(p.startswith(('src/', 'tests/', 'tools/', 'frontend/', 'migrations/')) for p in dirty if p):
        raise SystemExit('COMMIT_IMPLEMENTATION_FIRST')
    target = (ROOT / args.evidence_dir).resolve()
    if not target.is_relative_to((ROOT / 'docs/evidence').resolve()):
        raise SystemExit('EVIDENCE_DIRECTORY_REQUIRED')
    target.mkdir(parents=True, exist_ok=True)
    xml = ROOT / '.tmp' / ('frontend-backend-' + head[:12] + '.xml')
    env = dict(os.environ, PYTHONPATH='src', COMMERCE_RUN_MYSQL_TESTS='1',
        COMMERCE_MODEL_PROVIDER='mock', COMMERCE_MODEL_NETWORK_ENABLED='false', PYTHONIOENCODING='utf-8')
    original = (ROOT / args.baseline_evidence).resolve()
    if not original.is_relative_to((ROOT / 'docs/evidence').resolve()):
        raise SystemExit('BASELINE_EVIDENCE_REQUIRED')
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    commands = [[sys.executable, '-m', 'pytest', '-vv', '-p', 'no:cacheprovider',
        '--basetemp=.tmp/frontend-backend-' + head[:12], '--junitxml=' + str(xml)],
        [sys.executable, '-m', 'pip', 'check'],
        [sys.executable, '-m', 'compileall', '-q', 'src', 'tests', 'tools', 'migrations'],
        [sys.executable, '-m', 'tools.deepseek_connectivity'],
        [sys.executable, '-m', 'tools.s01_model_evaluation'],
        [sys.executable, '-m', 'tools.s01_model_evaluation', '--offline-suite'],
        [sys.executable, '-m', 'tools.s01_backend_observation_smoke'],
        [sys.executable, '-m', 'tools.s01_teaching_dataset'],
        [sys.executable, 'docs/evidence/D-S01-DATA-01/verify_offline.py']]
    runs = []
    for command in commands:
        run = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
        runs.append(dict(command=['python', *command[1:]], exitCode=run.returncode,
            result='PASS' if run.returncode == 0 else 'FAIL', output=run.stdout))
        print(json.dumps(dict(command=command[1:3], exitCode=run.returncode)), flush=True)
    cases = []
    for case in ET.parse(xml).getroot().iter('testcase'):
        state = 'FAIL' if case.find('failure') is not None else 'ERROR' if case.find('error') is not None else 'SKIP' if case.find('skipped') is not None else 'PASS'
        cases.append(dict(classname=case.get('classname'), name=case.get('name'), result=state))
    baseline = json.loads(original.read_text(encoding='utf-8'))['cases']
    old = {(x['classname'], x['name']) for x in baseline}
    new = {(x['classname'], x['name']) for x in cases}
    sys.path.insert(0, str(ROOT / 'src'))
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database, assert_migration_target
    from sqlalchemy import text
    os.environ.update(COMMERCE_MODEL_PROVIDER='mock', COMMERCE_MODEL_NETWORK_ENABLED='false')
    settings = load_settings(); assert_migration_target(settings)
    database = Database(settings)
    try:
        with database.engine.connect() as conn:
            meta = conn.execute(text('SELECT VERSION(), DATABASE(), @@session.time_zone, @@transaction_isolation')).one()
            heads = conn.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
    finally:
        database.close()
    after = hashlib.sha256(original.read_bytes()).hexdigest()
    suite = dict(total=len(cases), passed=sum(x['result'] == 'PASS' for x in cases),
        failed=sum(x['result'] == 'FAIL' for x in cases), errors=sum(x['result'] == 'ERROR' for x in cases),
        skipped=sum(x['result'] == 'SKIP' for x in cases), baselineCases=len(old), baselineCasesPreserved=old <= new)
    result = 'PASS' if old <= new and before == after and cases and all(x['result'] == 'PASS' for x in cases) and all(r['exitCode'] == 0 for r in runs) else 'FAIL'
    report = dict(result=result, testedCommit=head, capturedAt=datetime.now(timezone.utc).isoformat(),
        scope='Existing backend regression and current S01 fixes. Offline ERP/model fixtures, real isolated MySQL and independent processes.',
        database=dict(server=meta[0], name=meta[1], timezone=meta[2], isolation=meta[3], migrationHeads=heads),
        suite=suite, cases=cases, runs=runs, originalEvidenceSha256=before, originalEvidencePreserved=before == after,
        erpNetworkRequests=0, paidModelRequests=0, procurementWrites=0, enterpriseGates='BLOCKED')
    # Only publish safe aggregate evidence; any unexpected credentials stop publication.
    content = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    from dotenv import dotenv_values
    protected = [v for k, v in dotenv_values(ROOT / '.env', interpolate=False).items() if v and any(s in k.upper() for s in ['PASSWORD', 'SECRET', 'SIGNING_KEY', 'API_KEY'])]
    if any(value in content for value in protected):
        raise SystemExit('SENSITIVE_OUTPUT_WITHHELD')
    (target / 'backend-regression.json').write_bytes(content.encode('utf-8'))
    print(json.dumps(dict(result=result, suite=suite)))
    return 0 if result == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
