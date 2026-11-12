"""Capture reproducible C-01 OFFLINE-model / real-isolated-MySQL evidence at a fixed Git commit."""
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def main():
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    tracked=subprocess.check_output(["git","diff","--name-only","HEAD"],cwd=ROOT,text=True).splitlines()
    implementation=lambda p:p.startswith(("src/","tests/","tools/verify_c01.py","tools/deepseek_connectivity.py")) or p in {".env.example","pyproject.toml","requirements.lock"}
    if any(implementation(p) for p in tracked): raise RuntimeError("Commit implementation before fixed-commit verification")
    env=dict(os.environ,COMMERCE_RUN_MYSQL_TESTS="1",COMMERCE_MODEL_PROVIDER="mock",COMMERCE_MODEL_NETWORK_ENABLED="false",
        PYTHONIOENCODING="utf-8")
    overrides={k:env[k] for k in ["COMMERCE_RUN_MYSQL_TESTS","COMMERCE_MODEL_PROVIDER","COMMERCE_MODEL_NETWORK_ENABLED"]}
    target=ROOT/"docs/evidence/C-01/verification.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    xml_path=ROOT/".tmp"/("c01-fixed-"+head[:12]+".xml")
    runs=[]
    commands=[
        [sys.executable,"-m","pytest","-vv","-p","no:cacheprovider","--basetemp=.tmp/c01-fixed-"+head[:12],"--junitxml="+str(xml_path)],
        [sys.executable,"-m","pip","check"],
        [sys.executable,"-m","compileall","-q","src","tests","tools/deepseek_connectivity.py","tools/verify_c01.py"],
        [sys.executable,"-m","tools.deepseek_connectivity"],
    ]
    for command in commands:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,encoding="utf-8",errors="replace")
        runs.append(dict(command=["python",*command[1:]],environmentOverrides=overrides,exitCode=result.returncode,
            result="PASS" if result.returncode==0 else "FAIL",rawOutput=result.stdout))
    cases=[]
    if xml_path.is_file():
        for case in ET.parse(xml_path).getroot().iter("testcase"):
            status="FAIL" if case.find("failure") is not None else "ERROR" if case.find("error") is not None else "SKIP" if case.find("skipped") is not None else "PASS"
            cases.append(dict(classname=case.get("classname"),name=case.get("name"),seconds=case.get("time"),result=status))
    previous=json.loads((ROOT/"docs/evidence/ab-review-fix/verification.json").read_text(encoding="utf-8"))
    old={(c["classname"],c["name"]) for c in previous["cases"]}
    actual={(c["classname"],c["name"]) for c in cases}
    new=[c for c in cases if (c["classname"],c["name"]) not in old]
    # Only authorized metadata; never serialize Settings or connection arguments.
    os.environ.update(overrides)
    from commerce_hub.bootstrap.settings import load_settings
    from commerce_hub.infrastructure.database import Database,assert_migration_target
    from sqlalchemy import text
    config=load_settings()
    assert_migration_target(config)
    db=Database(config)
    try:
        with db.engine.connect() as conn:
            row=conn.execute(text("SELECT VERSION(), DATABASE(), @@session.time_zone, @@transaction_isolation")).one()
            heads=conn.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        metadata=dict(mysqlServer=row[0],database=row[1],timeZone=row[2],isolation=row[3],migrationHeads=heads)
    finally: db.close()
    evidence=dict(scope="C-01 MOCK/OFFLINE_TRANSPORT plus original A/B real MySQL/API/Worker regression; ZERO real model calls",
        date="2026-11-12",capturedAt=datetime.now(timezone.utc).isoformat(),baselineCommit="c0e5af096a41c680b0caff4b26424367bd6d0abe",
        testedCommit=head,environment=dict(python=sys.version,os="Windows",runtime=".tmp/stage-a-clean",overrides=overrides),
        versions={p:importlib.metadata.version(p) for p in ["SQLAlchemy","PyMySQL","alembic","fastapi","pydantic","pytest","starlette","httpx"]},
        databaseMetadata=metadata,runs=runs,cases=cases,newCases=new,
        suite=dict(total=len(cases),passed=sum(c["result"]=="PASS" for c in cases),failed=sum(c["result"]=="FAIL" for c in cases),
            errors=sum(c["result"]=="ERROR" for c in cases),skipped=sum(c["result"]=="SKIP" for c in cases),original187Preserved=old<=actual,addedCases=len(new)),
        officialDocumentation=dict(checkedOn="2026-11-12",sources=["https://api-docs.deepseek.com/quick_start/pricing","https://api-docs.deepseek.com/api/create-chat-completion"],
            modelId="deepseek-flash",documentedRevision="DeepSeek-V4.1-Flash-1017",protocol="Official chat/completions; JSON Output + local Schema; thinking disabled; nonstreaming; no tools",
            peakCeilingUsdPerMillion=dict(inputCacheMiss="0.30",output="1.20"),realProtocolVerification="NOT_RUN"),
        safety=dict(realModelCalls=0,erpCalls=0,procurementWrites=0,secretValuesPrinted=False,localSecretFileModified=False,otherDatabasesModified=False,
            realAiAccess="BLOCKED",c04="NOT_RUN",mockNotRealAcceptance=True),
        limitations=["DeepSeek real connectivity, billing reconciliation, data/terms/region approval and C-04 purpose evaluation NOT_RUN.",
            "DeepSeek known token counts with unknown actual monetary charge retain the whole original allowance; no estimated settlement.",
            "Provider alias is not an immutable revision; undocumented model mismatch fails closed.",
            "Current Context/Prompt/Schema are synthetic engineering only; future S01 Handler owns semantic/fact/support-reference checks.",
            "Concurrency is durable per task and bounded per gateway process, not a global deployment quota across all tasks.",
            "Existing local provider setting is not accepted by the new enum; local file untouched; Mock is explicitly selected for regression."],
        executionHistory=["Precommit full regression:270 PASS/0 FAIL/0 ERROR/0 SKIP, one existing deprecation warning.",
            "First fixed implementation 2f3aa8cebcf6943e2ba2f0c6153319674b6e80f8:270 PASS; pip check/compileall/default disabled probe PASS. Final-audit cancellation/deadline race then hardened with two new tests; final testedCommit below supersedes that implementation.",
            "Initial new authority-immutability test used a wrong helper import; corrected to exercise actual B01/B02 public APIs.",
            "Sandbox blocked pytest temporary-folder access; controlled execution passed.",
            "Initial local provider configuration validation failed safely; no secrets printed and .env unchanged.",
            "Initial cancellation expectation TASK_STOPPED corrected to allow O01 lease revocation LEASE_LOST; late result remains unavailable."],
        recommendation="C-01 REVIEW only; independent acceptance required")
    target.write_bytes((json.dumps(evidence,ensure_ascii=False,indent=2)+"\n").encode())
    print(json.dumps(dict(testedCommit=head,suite=evidence["suite"],runs=[dict(command=r["command"][1:3],result=r["result"]) for r in runs]),ensure_ascii=False))
    return 0 if all(r["exitCode"]==0 for r in runs) and old<=actual and cases and all(c["result"]=="PASS" for c in cases) else 1


if __name__=="__main__":
    raise SystemExit(main())
