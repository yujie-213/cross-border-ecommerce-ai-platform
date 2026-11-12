"""Reproducible engineering-only API/Worker/MySQL demonstration (requires dev deps)."""
import json

from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.infrastructure.database import Database, assert_migration_target
from tests.support.s01_process import S01ProcessHarness


def main():
    settings = load_settings()
    assert_migration_target(settings)
    if settings.environment != "test":
        raise ValueError("Demo requires COMMERCE_ENVIRONMENT=test")
    database = Database(settings)
    if not database.schema_ready():
        database.close()
        raise ValueError("Run the explicit authorized migration first")
    harness = S01ProcessHarness(database, settings)
    try:
        harness.start_api()
        task, _, _ = harness.submit()
        task_id = task["taskRef"]["taskId"]
        harness.start_worker()
        harness.wait_state(task_id, "SUCCEEDED")
        report = harness.report(task_id)
        data = report["dataReport"]
        print(json.dumps(dict(sourceNature=report["sourceNature"], completeness=report["completeness"],
            taskRef=report["taskRef"], reportRef=report["reportRef"], snapshotRef=report["snapshotRef"],
            quality=data["quality"], supplyDemand=data["supplyDemand"],
            ai=report["analysisReport"]["ai"], realAdmission="BLOCKED", procurementEligible=False), indent=2))
    finally:
        harness.close()
        database.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        raise SystemExit("Engineering demo failed safely; no credentials or raw database errors displayed") from None
