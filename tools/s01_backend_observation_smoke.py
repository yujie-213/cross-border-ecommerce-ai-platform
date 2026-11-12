"""Explicit real-MySQL/API/Worker smoke for one fixed ERP observation.

The default is NOT_RUN.  ``--run-real-backend`` is required.  This tool never
contacts ERP or a model provider and never clears shared tables.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import select, text, update

from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.governance.access.tables import grants
from commerce_hub.infrastructure.database import (
    AUTHORIZED_TEST_DATABASE,
    Database,
    assert_migration_target,
    migrate,
)
from commerce_hub.orchestration.tables import reports, tasks
from tests.support.backend import BackendHarness
from tools.s01_candidate_discovery import build_best_observation


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIVATE = ROOT / "data/private/s01-backend-erp-discovery/run-20261112T110305Z-edff865b/discovery-private.json"
EVIDENCE = ROOT / "docs/evidence/S01-BACKEND/erp/real-backend-workflow.json"


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n").encode()


def _digest(value: object) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()


def _selected_private(package: dict, candidate_alias: str) -> dict:
    for candidate in package.get("candidates", []):
        sku = candidate.get("sku")
        if isinstance(sku, str) and "sku-" + _digest(sku)[:20] == candidate_alias:
            return candidate
    raise RuntimeError("RECOMMENDED_PRIVATE_CANDIDATE_NOT_FOUND")


def _private_values(candidate: dict) -> set[str]:
    values = {candidate["sku"]}
    private_keys = {"id", "store_id", "wid", "listing_id", "order_sn", "purchase_order_sn",
                    "tracking_no", "supplier_id", "supplier_code", "source_plan_no"}
    for capture in candidate["captures"].values():
        for row in capture.get("rows") or []:
            for key in private_keys:
                value = row.get(key)
                if value is not None and len(str(value)) >= 6:
                    values.add(str(value))
    return values


def _assert_no_private_values(value: object, candidate: dict) -> None:
    rendered = json.dumps(value, ensure_ascii=False, default=str)
    leaked = [item for item in _private_values(candidate) if item in rendered]
    forbidden_fields = ["minimum_amount", "unit_price", '"amount"', '"cost"', '"price"']
    if leaked or any(field in rendered for field in forbidden_fields):
        raise RuntimeError("PUBLIC_REPORT_PRIVATE_VALUE_LEAK")


def run(private_path: Path) -> dict:
    os.environ.update(COMMERCE_ENVIRONMENT="test", COMMERCE_MODEL_PROVIDER="mock",
                      COMMERCE_MODEL_NETWORK_ENABLED="false")
    settings = load_settings()
    if settings.environment != "test" or settings.db_name != AUTHORIZED_TEST_DATABASE:
        raise RuntimeError("AUTHORIZED_ISOLATED_MYSQL_REQUIRED")
    migrate(settings)
    assert_migration_target(settings)
    database = Database(settings)
    harness = BackendHarness(database, settings, entries=[], mock=False)
    try:
        projection = build_best_observation(private_path, tenant_id=harness.tenant)
        entry = {"kind": "OBSERVATION", "payload": projection}
        harness.entries = [entry]
        harness.scope = projection["scope"]
        private_catalog = private_path.resolve().parent / ("backend-catalog-" + uuid4().hex + ".json")
        private_catalog.write_bytes(_json_bytes(harness.entries))
        harness.environment.update(COMMERCE_S01_CATALOG_PATH=str(private_catalog),
                                   COMMERCE_S01_EXPLANATION_MODE="off",
                                   COMMERCE_MODEL_PROVIDER="mock",
                                   COMMERCE_MODEL_NETWORK_ENABLED="false")
        with database.engine.begin() as connection:
            changed = connection.execute(update(grants).where(
                grants.c.tenant_id == harness.tenant,
                grants.c.principal_id == harness.principal_id,
            ).values(scope=harness.scope)).rowcount
        if changed <= 0:
            raise RuntimeError("RANDOM_TENANT_GRANTS_NOT_UPDATED")

        private_package = json.loads(private_path.read_text(encoding="utf-8"))
        selected = _selected_private(private_package, projection["scope"]["canonicalSkuIds"][0])
        harness.start_api()
        options = harness.client.get("/api/v1/s01/options")
        if options.status_code != 200 or len(options.json().get("mappedChoices", [])) != 1:
            raise RuntimeError("OBSERVATION_OPTION_NOT_AVAILABLE")
        if options.json()["mappedChoices"][0]["scope"] != harness.scope:
            raise RuntimeError("OBSERVATION_OPTION_SCOPE_MISMATCH")
        outside_options = harness.client.get("/api/v1/s01/options", params={"canonicalSkuId": "outside"})
        no_auth = harness.client.get("/api/v1/s01/options", headers={"Authorization": ""})
        if outside_options.status_code != 200 or outside_options.json().get("mappedChoices") != [] or no_auth.status_code != 401:
            raise RuntimeError("OBSERVATION_OPTIONS_PERMISSION_FAILURE")

        task, body, command_key = harness.submit(entry=entry)
        task_id = task["taskRef"]["taskId"]
        outside_body = json.loads(json.dumps(body))
        outside_body["scope"]["canonicalSkuIds"] = ["outside"]
        outside_create = harness.client.post("/api/v1/analysis-tasks", json=outside_body,
                                             headers={"Idempotency-Key": uuid4().hex})
        if outside_create.status_code not in {403, 422}:
            raise RuntimeError("OBSERVATION_CREATE_SCOPE_NOT_REJECTED")
        harness.start_worker()
        terminal = harness.wait_state(task_id, "SUCCEEDED")
        report = harness.report(task_id)
        supply = report["dataReport"]["supplyDemand"]
        ai = report["analysisReport"]["ai"]
        if (report["sourceNature"] != "TEACHING_ERP_OBSERVED" or report["completeness"] != "BLOCKED"
            or supply != {"baseline": None, "candidates": [], "limitations": ["DATA_QUALITY_BLOCKED"], "selection": None}
            or ai["status"] != "NOT_ATTEMPTED"):
            raise RuntimeError("OBSERVATION_BLOCKED_RESULT_MISMATCH")
        budget = harness.budget(task_id)
        if budget["reserved_calls"] != 0 or budget["used_calls"] != 0 or harness.audit_count(task_id, "MODEL_SENT") != 0:
            raise RuntimeError("OBSERVATION_MODEL_BUDGET_NOT_ZERO")
        if harness.audit_count(task_id, "REPORT_PUBLISHED") != 1:
            raise RuntimeError("OBSERVATION_REPORT_PUBLICATION_COUNT_INVALID")

        evidence_views = []
        for item in report["dataReport"]["evidence"]:
            response = harness.client.get(f"/api/v1/analysis-tasks/{task_id}/evidence/{item['evidenceId']}")
            if response.status_code != 200:
                raise RuntimeError("OBSERVATION_EVIDENCE_NOT_RESOLVABLE")
            evidence_views.append(response.json())
        _assert_no_private_values({"report": report, "evidence": evidence_views, "options": options.json()}, selected)
        if {"manifest", "inputProjection", "sourcePackage"} & set(report["dataReport"]):
            raise RuntimeError("OBSERVATION_INTERNAL_FIELDS_EXPOSED")

        replay = harness.client.post("/api/v1/analysis-tasks", json=body,
                                     headers={"Idempotency-Key": command_key})
        if replay.status_code != 202 or replay.json().get("reportRef") != report["reportRef"]:
            raise RuntimeError("OBSERVATION_IDEMPOTENCY_FAILURE")
        query = dict(storeId=harness.scope["storeIds"][0], warehouseId=harness.scope["warehouseIds"][0],
                     canonicalSkuId=harness.scope["canonicalSkuIds"][0], scenarioId="S01_BACKEND")
        history = harness.client.get("/api/v1/analysis-tasks", params=query)
        outside_history = harness.client.get("/api/v1/analysis-tasks", params=dict(query, canonicalSkuId="outside"))
        if (history.status_code != 200 or task_id not in {x["taskRef"]["taskId"] for x in history.json()["items"]}
            or outside_history.status_code != 403):
            raise RuntimeError("OBSERVATION_HISTORY_PERMISSION_FAILURE")

        harness.api.stop()
        harness.start_api()
        restarted = harness.report(task_id)
        if restarted != report:
            raise RuntimeError("OBSERVATION_RESTART_READ_MISMATCH")
        _assert_no_private_values(restarted, selected)

        with database.engine.connect() as connection:
            db_meta = connection.execute(text(
                "SELECT VERSION(), DATABASE(), @@session.time_zone, @@transaction_isolation"
            )).one()
            persisted = connection.execute(select(tasks.c.state, tasks.c.scenario_id).where(
                tasks.c.tenant_id == harness.tenant, tasks.c.task_id == task_id)).one()
            report_count = connection.scalar(select(text("COUNT(*)")).select_from(reports).where(
                reports.c.tenant_id == harness.tenant, reports.c.task_id == task_id))
        result = {
            "schemaVersion": "s01-real-backend-observation-v1",
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "result": "PASS",
            "source": "FIXED_TEACHING_ERP_NETWORK_CAPTURE_REPLAY",
            "erpRequestsThisRun": 0,
            "realModelRequests": 0,
            "procurementWrites": 0,
            "database": {"server": db_meta[0], "name": db_meta[1], "timeZone": db_meta[2],
                         "isolation": db_meta[3], "cleared": False},
            "processes": {"api": "INDEPENDENT", "worker": "INDEPENDENT", "apiRestarted": True},
            "task": {"state": terminal["state"], "persistedState": persisted[0],
                     "scenarioId": persisted[1], "reportPersisted": report_count == 1},
            "business": {"completeness": report["completeness"], "b01Executed": False,
                         "candidateCount": len(supply["candidates"]), "limitations": supply["limitations"],
                         "procurementEligible": report["dataReport"]["scenarioSupplement"]["procurementEligible"]},
            "model": {"status": ai["status"], "reservedCalls": budget["reserved_calls"],
                      "usedCalls": budget["used_calls"], "sentAuditCount": 0},
            "verification": {"idempotency": "PASS", "evidenceCount": len(evidence_views),
                             "history": "PASS", "restartRead": "PASS", "exactPermission": "PASS",
                             "publicPrivateLeakScan": "PASS"},
            "scope": harness.scope,
            "projectionRevision": projection["revision"],
            "privateRefs": {"discovery": private_path.relative_to(ROOT).as_posix(),
                            "catalog": private_catalog.relative_to(ROOT).as_posix()},
            "safety": {"sourceSynthetic": projection["sourceSynthetic"],
                       "ownerConfirmed": projection["ownerConfirmed"],
                       "revalidationFailed": projection["revalidationFailed"],
                       "realBusinessAdmission": "BLOCKED", "rawSourceIdsPublished": False,
                       "monetaryFieldsPublished": False},
        }
        _assert_no_private_values(result, selected)
        return result
    finally:
        harness.close()
        database.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-real-backend", action="store_true")
    parser.add_argument("--private-discovery", type=Path, default=DEFAULT_PRIVATE)
    args = parser.parse_args()
    if not args.run_real_backend:
        print(json.dumps({"result": "NOT_RUN", "reason": "EXPLICIT_REAL_BACKEND_FLAG_REQUIRED"}))
        return 0
    try:
        result = run(args.private_discovery.resolve())
        EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
        EVIDENCE.write_bytes(_json_bytes(result))
        print(json.dumps({"result": result["result"], "taskState": result["task"]["state"],
                          "businessCompleteness": result["business"]["completeness"],
                          "evidenceRef": EVIDENCE.relative_to(ROOT).as_posix()}))
        return 0
    except Exception as error:
        print(json.dumps({"result": "FAIL", "code": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
