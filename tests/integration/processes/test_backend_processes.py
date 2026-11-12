"""Real MySQL/API/worker, explicitly simulated A-E and separate source observations."""
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import update

from commerce_hub.governance.access.tables import grants
from tests.support.backend import BackendHarness, cases

pytestmark = pytest.mark.mysql


def test_backend_five_cases_history_relation_permissions_and_restart(database, mysql_settings):
    entries = cases()
    h = BackendHarness(database, mysql_settings)
    try:
        h.start_api()
        options = h.client.get("/api/v1/s01/options")
        assert options.status_code == 200 and len(options.json()["mappedChoices"]) == 5
        assert h.client.get("/api/v1/s01/options", params={"canonicalSkuId":"outside"}).json()["mappedChoices"] == []
        assert h.client.get("/api/v1/s01/options", headers={"Authorization":""}).status_code == 401
        h.start_worker()
        reports = {}
        for key, entry in entries.items():
            task, body, command = h.submit(entry=entry, previous=reports["A"]["reportRef"] if key == "B" else None)
            task_id = task["taskRef"]["taskId"]
            h.wait_state(task_id, "SUCCEEDED")
            report = h.report(task_id)
            reports[key] = report
            assert report["analysisReport"]["ai"]["status"] == "AVAILABLE"
            assert report["dataReport"]["scenarioSupplement"]["procurementEligible"] is False
            assert not {"sourcePackage", "inputProjection", "manifest"} & set(report["dataReport"])
            assert "sourceSku" not in str(report)
            for evidence in report["dataReport"]["evidence"]:
                response = h.client.get(f"/api/v1/analysis-tasks/{task_id}/evidence/{evidence['evidenceId']}")
                assert response.status_code == 200
            assert h.client.post("/api/v1/analysis-tasks", json=body, headers={"Idempotency-Key":command}).json()["reportRef"] == report["reportRef"]
        assert reports["A"]["dataReport"]["supplyDemand"]["candidates"][0]["quantity"] == "20"
        assert reports["B"]["dataReport"]["supplyDemand"]["limitations"] == ["NO_REPLENISHMENT_NEEDED"]
        assert reports["B"]["dataReport"]["scenarioSupplement"]["previousReportRef"] == reports["A"]["reportRef"]
        assert reports["C"]["dataReport"]["supplyDemand"]["baseline"]["stockoutRisk"] is True
        assert reports["D"]["completeness"] == "BLOCKED" and reports["E"]["completeness"] == "PARTIAL"
        query = dict(storeId="store-fixture", warehouseId="warehouse-fixture", canonicalSkuId="sku-fixture", limit=2)
        page = h.client.get("/api/v1/analysis-tasks", params=query)
        assert page.status_code == 200 and len(page.json()["items"]) == 2
        all_ids = [item["taskRef"]["taskId"] for item in page.json()["items"]]
        while page.json()["nextCursor"]:
            page = h.client.get("/api/v1/analysis-tasks", params=dict(query, before=page.json()["nextCursor"]))
            assert page.status_code == 200
            all_ids.extend(item["taskRef"]["taskId"] for item in page.json()["items"])
        assert len(set(all_ids)) == len(all_ids) == 5
        assert h.client.get("/api/v1/analysis-tasks", params=dict(query, before="missing")).status_code == 404
        assert h.client.get("/api/v1/analysis-tasks", params=dict(query, canonicalSkuId="outside")).status_code == 403
        h.api.stop(); h.start_api()
        assert h.report(reports["A"]["taskRef"]["taskId"]) == reports["A"]
        with database.engine.begin() as conn:
            conn.execute(update(grants).filter_by(tenant_id=h.tenant, principal_id=h.principal_id).values(scope=dict(h.scope, fields=["other"])))
        assert h.client.get("/api/v1/s01/options").json()["mappedChoices"] == []
        assert h.client.get("/api/v1/analysis-tasks", params=query).status_code == 403
        assert h.client.get("/api/v1/analysis-tasks/" + reports["A"]["taskRef"]["taskId"] + "/report").status_code == 404
    finally:
        h.close()


def test_backend_cancel_and_untrusted_package_do_not_publish(database, mysql_settings):
    h = BackendHarness(database, mysql_settings, mock=False)
    try:
        h.start_api()
        task, body, _ = h.submit()
        invalid = deepcopy(body)
        invalid["parameters"]["path"] = "outside"
        assert h.client.post("/api/v1/analysis-tasks", json=invalid, headers={"Idempotency-Key":uuid4().hex}).status_code == 422
        invalid = deepcopy(body); invalid["scope"]["canonicalSkuIds"] = ["outside"]
        assert h.client.post("/api/v1/analysis-tasks", json=invalid, headers={"Idempotency-Key":uuid4().hex}).status_code == 422
        task_id = task["taskRef"]["taskId"]
        assert h.client.post(f"/api/v1/analysis-tasks/{task_id}/cancel", json=dict(expectedRevision=task["revision"]),
            headers={"Idempotency-Key":uuid4().hex}).status_code == 200
        h.start_worker(); h.wait_state(task_id, "CANCELLED")
        assert h.client.get(f"/api/v1/analysis-tasks/{task_id}/report").status_code == 404
        assert h.budget(task_id)["used_calls"] == h.budget(task_id)["reserved_calls"] == 0
    finally:
        h.close()
