"""Real socket HTTP + independent Worker + actual isolated MySQL, synthetic inputs."""
import pytest

from commerce_hub.capabilities.forecasting import propose
from tests.support.s01 import example, snapshot
from tests.support.s01_process import S01ProcessHarness

pytestmark = pytest.mark.mysql


def test_actual_s01_api_worker_report_evidence_and_read_authorization(database, mysql_settings):
    harness = S01ProcessHarness(database, mysql_settings)
    other = S01ProcessHarness(database, mysql_settings)
    try:
        harness.start_api()
        task, payload, key = harness.submit()
        task_id = task["taskRef"]["taskId"]
        prefix = "/api/v1/analysis-tasks/" + task_id
        assert harness.client.get(prefix + "/report").status_code == 404
        harness.start_worker()
        harness.wait_state(task_id, "SUCCEEDED")
        report = harness.report(task_id)
        data = report["dataReport"]
        assert data["supplyDemand"] == propose(snapshot())
        assert report["analysisReport"]["ai"]["status"] == "NOT_ATTEMPTED"
        assert report["planVersion"] == "1" and report["completeness"] == "RULES_ONLY"
        for evidence in data["evidence"]:
            response = harness.client.get(prefix + "/evidence/" + evidence["evidenceId"])
            assert response.status_code == 200 and response.json()["locator"] == evidence
        assert harness.client.get(prefix + "/evidence/unknown").status_code == 404
        replay = harness.client.post("/api/v1/analysis-tasks", json=payload, headers={"Idempotency-Key": key})
        assert replay.json()["reportRef"] == report["reportRef"]
        assert harness.audit_count(task_id, "REPORT_PUBLISHED") == 1
        # API restart returns the exact persisted result, not recomputed current data.
        harness.api.stop()
        harness.start_api()
        assert harness.report(task_id) == report
        other.start_api()
        assert other.client.get(prefix + "/report").status_code == 404
        assert other.client.get(prefix + "/evidence/" + data["evidence"][0]["evidenceId"]).status_code == 404
        assert harness.client.get(prefix + "/report", headers={"Authorization": ""}).status_code == 401
        from commerce_hub.governance.access import AccessControl
        access = AccessControl(database.engine, harness.issuer, harness.audience, harness.key)
        with database.engine.begin() as conn:
            access.revoke_token(conn, access.authenticate(harness.token))
        assert harness.client.get(prefix + "/report").status_code == 403
    finally:
        harness.close()
        other.close()


def test_s01_killed_worker_recovers_original_snapshot_report_budget_and_deadline(database, mysql_settings):
    harness = S01ProcessHarness(database, mysql_settings, recovery_fixture=True)
    try:
        harness.environment["COMMERCE_S01_TEST_DELAY"] = "2"
        harness.start_api()
        task, _, _ = harness.submit()
        task_id = task["taskRef"]["taskId"]
        original_deadline = harness.row(task_id)["deadline"]
        original_budget = harness.budget(task_id)
        original_parameters = harness.row(task_id)["parameters"]
        first = harness.start_worker()
        harness.wait_state(task_id, "RUNNING")
        first.stop(crash=True)
        assert harness.client.get("/api/v1/analysis-tasks/" + task_id + "/report").status_code == 404
        harness.start_worker()
        harness.wait_state(task_id, "SUCCEEDED")
        report = harness.report(task_id)
        assert harness.work(task_id)["attempt"] == 2
        assert harness.row(task_id)["deadline"] == original_deadline
        assert harness.row(task_id)["parameters"] == original_parameters == example()
        assert harness.budget(task_id) == original_budget
        assert report["snapshotRef"] == snapshot().snapshotId
        assert report["dataReport"]["supplyDemand"] == propose(snapshot())
        assert harness.audit_count(task_id, "REPORT_PUBLISHED") == harness.audit_count(task_id, "TASK_COMPLETED") == 1
    finally:
        harness.close()
