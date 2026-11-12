"""S01 business Handler in separate real HTTP/Worker processes, synthetic facts/Mock only."""
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import update

from commerce_hub.capabilities.forecasting import propose
from commerce_hub.governance.access.tables import grants
from commerce_hub.orchestration.tables import reports
from tests.support.s01 import example, snapshot
from tests.support.s01_process import S01ProcessHarness

pytestmark = pytest.mark.mysql


class BusinessHarness(S01ProcessHarness):
    def __init__(self, database, settings):
        super().__init__(database, settings)
        self.module = "commerce_hub.bootstrap.s01_business"
        self.environment.update(COMMERCE_MODEL_PROVIDER="mock", COMMERCE_MODEL_NETWORK_ENABLED="false")

    def submit(self, *, parameters=None, key=None, previous=None):
        body = dict(analysisMode="SINGLE", scenarioId="ENGINEERING_S01_BUSINESS",
            scope={k: v for k, v in self.scope.items() if k != "tenantId"},
            parameters=example() if parameters is None else parameters)
        if previous is not None:
            body["previousReportRef"] = previous
        key = key or uuid4().hex
        response = self.client.post("/api/v1/analysis-tasks", json=body, headers={"Idempotency-Key": key})
        assert response.status_code == 202, response.json().get("code")
        return response.json(), body, key


def test_business_api_worker_mock_report_relation_and_immutable_old_report(database, mysql_settings):
    h = BusinessHarness(database, mysql_settings)
    try:
        h.start_api()
        query = dict(storeId="store-fixture", warehouseId="warehouse-fixture", canonicalSkuId="sku-fixture")
        options = h.client.get("/api/v1/s01/options", params=query)
        assert options.status_code == 200
        assert options.json()["mappedChoices"] == [] and options.json()["realAdmission"] == "BLOCKED"
        assert h.client.get("/api/v1/s01/options", params=dict(query, storeId="outside")).status_code == 403
        assert h.client.get("/api/v1/s01/options", params=query, headers={"Authorization": ""}).status_code == 401
        task, body, key = h.submit()
        task_id = task["taskRef"]["taskId"]
        h.start_worker()
        h.wait_state(task_id, "SUCCEEDED")
        old = h.report(task_id)
        assert old["sourceNature"] == "SIMULATED_ENGINEERING"
        assert old["dataReport"]["supplyDemand"] == propose(snapshot())
        assert old["analysisReport"]["ai"]["status"] == "AVAILABLE"
        assert old["dataReport"]["scenarioSupplement"]["procurementEligible"] is False
        assert "inputProjection" not in old["dataReport"] and "manifest" not in old["dataReport"]
        assert h.budget(task_id)["used_calls"] == 1 and h.budget(task_id)["reserved_calls"] == 0
        assert h.client.post("/api/v1/analysis-tasks", json=body,
            headers={"Idempotency-Key": key}).json()["reportRef"] == old["reportRef"]
        for evidence in old["dataReport"]["evidence"]:
            assert h.client.get(f"/api/v1/analysis-tasks/{task_id}/evidence/{evidence['evidenceId']}").status_code == 200
        from sqlalchemy import select
        with database.engine.begin() as conn:
            persisted = dict(conn.execute(select(reports).filter_by(tenant_id=h.tenant, task_id=task_id)).mappings().one())
            damaged = deepcopy(persisted["payload"])
            damaged["scenarioVersion"] = "forged-version"
            # Even a recomputed storage digest cannot legitimize a cross-version payload.
            from commerce_hub.orchestration.service import TaskService
            conn.execute(update(reports).filter_by(tenant_id=h.tenant, task_id=task_id).values(
                payload=damaged, fingerprint=TaskService.fingerprint(damaged)))
        assert h.client.get(f"/api/v1/analysis-tasks/{task_id}/report").status_code == 404
        invalid_link = dict(body, previousReportRef=old["reportRef"])
        assert h.client.post("/api/v1/analysis-tasks", json=invalid_link,
            headers={"Idempotency-Key": uuid4().hex}).status_code == 404
        with database.engine.begin() as conn:
            conn.execute(update(reports).filter_by(tenant_id=h.tenant, task_id=task_id).values(
                payload=persisted["payload"], fingerprint="0" * 64))
        assert h.client.get(f"/api/v1/analysis-tasks/{task_id}/report").status_code == 404
        with database.engine.begin() as conn:
            conn.execute(update(reports).filter_by(tenant_id=h.tenant, task_id=task_id).values(
                payload=persisted["payload"], fingerprint=persisted["fingerprint"]))
        assert h.report(task_id) == old
        changed = example()
        changed["supply"][0]["availableDate"] = "2026-11-21"
        new_task, new_body, new_key = h.submit(parameters=changed, previous=old["reportRef"])
        new_id = new_task["taskRef"]["taskId"]
        h.wait_state(new_id, "SUCCEEDED")
        new = h.report(new_id)
        assert new_id != task_id and new["snapshotRef"] != old["snapshotRef"]
        assert new["dataReport"]["scenarioSupplement"]["previousReportRef"] == old["reportRef"]
        assert h.report(task_id) == old
        assert h.client.post("/api/v1/analysis-tasks", json=new_body,
            headers={"Idempotency-Key": new_key}).json()["taskRef"] == new_task["taskRef"]
        conflict = deepcopy(new_body)
        conflict.pop("previousReportRef")
        assert h.client.post("/api/v1/analysis-tasks", json=conflict,
            headers={"Idempotency-Key": new_key}).status_code == 409
        invalid = deepcopy(new_body)
        invalid["parameters"]["_previousReportRef"] = old["reportRef"]
        assert h.client.post("/api/v1/analysis-tasks", json=invalid,
            headers={"Idempotency-Key": uuid4().hex}).status_code == 422
        for reference in [dict(old["reportRef"], tenantId="other"),
                          dict(old["reportRef"], reportId="missing")]:
            invalid = dict(new_body, previousReportRef=reference)
            assert h.client.post("/api/v1/analysis-tasks", json=invalid,
                headers={"Idempotency-Key": uuid4().hex}).status_code == 404
        # Restart API and retain both independent persisted versions.
        h.api.stop()
        h.start_api()
        assert h.report(task_id) == old and h.report(new_id) == new
        with database.engine.begin() as conn:
            conn.execute(update(grants).filter_by(tenant_id=h.tenant, principal_id=h.principal_id,
                action="tasks:read").values(scope=dict(h.scope, fields=["other-field"])))
        assert h.client.get(f"/api/v1/analysis-tasks/{new_id}/report").status_code == 404
        assert h.client.post("/api/v1/analysis-tasks", json=new_body,
            headers={"Idempotency-Key": uuid4().hex}).status_code == 404
    finally:
        h.close()


def test_business_cancel_before_worker_never_calls_model_or_publishes(database, mysql_settings):
    h = BusinessHarness(database, mysql_settings)
    try:
        h.start_api()
        task, body, _ = h.submit()
        task_id = task["taskRef"]["taskId"]
        response = h.client.post(f"/api/v1/analysis-tasks/{task_id}/cancel",
            json={"expectedRevision": task["revision"]}, headers={"Idempotency-Key": uuid4().hex})
        assert response.status_code == 200
        h.start_worker()
        h.wait_state(task_id, "CANCELLED")
        assert h.client.get(f"/api/v1/analysis-tasks/{task_id}/report").status_code == 404
        assert h.budget(task_id)["used_calls"] == h.budget(task_id)["reserved_calls"] == 0
        assert h.audit_count(task_id, "MODEL_SENT") == h.audit_count(task_id, "REPORT_PUBLISHED") == 0
        bad = dict(body, previousReportRef=dict(tenantId=h.tenant, reportId=task_id))
        assert h.client.post("/api/v1/analysis-tasks", json=bad,
            headers={"Idempotency-Key": uuid4().hex}).status_code == 404
    finally:
        h.close()
