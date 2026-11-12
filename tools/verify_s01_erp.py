"""Fixed-commit teaching ERP regression; offline fixtures and separate real-source evidence."""
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    paths = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=ROOT, text=True).splitlines()
    paths += subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    if any(p.startswith(("src/", "tests/", "tools/")) or p in
           {"pyproject.toml", "requirements.lock", ".env.example"} for p in paths):
        raise RuntimeError("Commit implementation before fixed-commit verification")
    overrides = dict(COMMERCE_RUN_MYSQL_TESTS="1", COMMERCE_MODEL_PROVIDER="mock",
                     COMMERCE_MODEL_NETWORK_ENABLED="false", PYTHONIOENCODING="utf-8")
    env = dict(os.environ, **overrides)
    target = ROOT / "docs/evidence/D-S01-LIVE-01/verification.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    xml_path = ROOT / ".tmp" / ("s01-erp-fixed-" + head[:12] + ".xml")
    commands = [
        [sys.executable, "-m", "pytest", "-vv", "-p", "no:cacheprovider",
         "--basetemp=.tmp/s01-erp-fixed-" + head[:12], "--junitxml=" + str(xml_path)],
        [sys.executable, "-m", "pip", "check"],
        [sys.executable, "-m", "compileall", "-q", "src", "tests", "tools/verify_s01_erp.py", "tools/s01_erp_readonly.py"],
        [sys.executable, "-m", "tools.deepseek_connectivity"],
        [sys.executable, "docs/evidence/D-S01-DATA-01/verify_offline.py"],
    ]
    runs = []
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
        runs.append(dict(command=["python", *command[1:]], environmentOverrides=overrides,
            exitCode=result.returncode, result="PASS" if result.returncode == 0 else "FAIL", rawOutput=result.stdout))
        print(json.dumps(dict(command=command[1:3], exitCode=result.returncode)), flush=True)
    cases = []
    if xml_path.is_file():
        for case in ET.parse(xml_path).getroot().iter("testcase"):
            status = "FAIL" if case.find("failure") is not None else "ERROR" if case.find("error") is not None else "SKIP" if case.find("skipped") is not None else "PASS"
            cases.append(dict(classname=case.get("classname"), name=case.get("name"), seconds=case.get("time"), result=status))
    old_evidence = json.loads((ROOT / "docs/evidence/D-S01-DEV-01/verification.json").read_text(encoding="utf-8"))
    old = {(c["classname"], c["name"]) for c in old_evidence["cases"]}
    actual = {(c["classname"], c["name"]) for c in cases}
    os.environ.update(overrides)
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database, assert_migration_target
    from sqlalchemy import text
    config = load_settings()
    assert_migration_target(config)
    db = Database(config)
    try:
        with db.engine.connect() as conn:
            row = conn.execute(text("SELECT VERSION(), DATABASE(), @@session.time_zone, @@transaction_isolation")).one()
            heads = conn.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        metadata = dict(mysqlServer=row[0], database=row[1], timeZone=row[2], isolation=row[3], migrationHeads=heads)
    finally:
        db.close()
    suite = dict(total=len(cases), passed=sum(c["result"] == "PASS" for c in cases),
        failed=sum(c["result"] == "FAIL" for c in cases), errors=sum(c["result"] == "ERROR" for c in cases),
        skipped=sum(c["result"] == "SKIP" for c in cases), baselineCases=len(old),
        baselineCasesPreserved=old <= actual, addedCases=len(actual - old))
    evidence = dict(scope="D-S01-LIVE-01 regression: OFFLINE transport/observation fixtures plus legacy Mock; real isolated MySQL/API/Worker. Actual ERP network evidence is separate source-index.json.",
        date="2026-11-12", capturedAt=datetime.now(timezone.utc).isoformat(), testedCommit=head,
        baselineCommit="b1813e5e851ad1bb513f550118dc973e6605b97b", environment=dict(python=sys.version,
            os="Windows", runtime=".tmp/stage-a-clean", overrides=overrides),
        versions={p: importlib.metadata.version(p) for p in ["SQLAlchemy", "PyMySQL", "alembic", "fastapi", "pydantic", "pytest", "starlette", "httpx"]},
        databaseMetadata=metadata, runs=runs, cases=cases, suite=suite,
        regressionInput="OFFLINE_CONTRACT_FIXTURES_NOT_LIVE_ERP", aiProvider="MOCK_FOR_LEGACY_TESTS; NOT_ATTEMPTED_FOR_TEACHING", realSourceEvidenceRef="docs/evidence/D-S01-LIVE-01/source-index.json",
        safety=dict(regressionErpRequests=0, realModelRequests=0, procurementWrites=0, otherDatabasesModified=False,
            secretValuesPrinted=False, localEnvModified=False, realAdmission="BLOCKED"),
        limitations=["Owner confirmed new SKU-B; data/rules/formal safety/model gates remain unadmitted. No claim to recover SKU-A.",
            "Current real-source pipeline produces a BLOCKED admission report only. Positive real B01/B02 business calculations remain NOT_RUN.",
            "Real source evidence and explicit fixed earlier observation replay are separated from offline regression. Later ERP503 is not replaced by Mock or called latest success.",
            "AI failure preserves legal deterministic output; model replay never changes original task budget or call identifiers.",
            "Real ERP reads are documented separately; no UI, real DeepSeek, procurement writes or business/production acceptance."],
        recommendation="REVIEW; await user and Xingxing independent acceptance")
    target.write_bytes((json.dumps(evidence, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(dict(testedCommit=head, suite=suite), ensure_ascii=False))
    return 0 if cases and old <= actual and all(c["result"] == "PASS" for c in cases) and all(r["exitCode"] == 0 for r in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
