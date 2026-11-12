"""Real isolated MySQL/API/independent Worker; OFFLINE observation DTO fixtures, no ERP network."""
from copy import deepcopy
from uuid import uuid4
import pytest
from sqlalchemy import update
from commerce_hub.governance.access.tables import grants
from tests.support.teaching_process import TeachingProcessHarness

pytestmark=pytest.mark.mysql


def test_teaching_admission_process_preserves_source_blocking_fixed_reports_and_current_auth(database,mysql_settings):
    h=TeachingProcessHarness(database,mysql_settings)
    try:
        h.start_api();assert h.client.get("/health/ready").json()["scope"]=="TEACHING_ERP_ADMISSION_ONLY"
        task,body,key=h.submit();tid=task["taskRef"]["taskId"]
        h.start_worker();h.wait_state(tid,"SUCCEEDED")
        report=h.report(tid)
        assert report["sourceNature"]=="TEACHING_ERP_OBSERVED" and report["completeness"]=="BLOCKED"
        assert report["dataReport"]["supplyDemand"]==dict(baseline=None,candidates=[],limitations=["DATA_QUALITY_BLOCKED"],selection=None)
        assert report["dataReport"]["scenarioSupplement"]["engineeringFixture"] is False
        assert report["analysisReport"]["ai"]["status"]=="NOT_ATTEMPTED"
        assert "manifest" not in report["dataReport"] and "observationProjection" not in report["dataReport"]
        assert h.budget(tid)["used_calls"]==h.budget(tid)["reserved_calls"]==0
        assert h.audit_count(tid,"MODEL_SENT")==0 and h.audit_count(tid,"REPORT_PUBLISHED")==1
        evidence=report["dataReport"]["evidence"][0]
        assert h.client.get(f"/api/v1/analysis-tasks/{tid}/evidence/{evidence['evidenceId']}").status_code==200
        assert h.client.post("/api/v1/analysis-tasks",json=body,headers={"Idempotency-Key":key}).json()["reportRef"]==report["reportRef"]
        bad=deepcopy(body);bad["parameters"]["packageRef"]="unknown"
        assert h.client.post("/api/v1/analysis-tasks",json=bad,headers={"Idempotency-Key":uuid4().hex}).status_code==422
        h.api.stop();h.start_api();assert h.report(tid)==report
        with database.engine.begin() as conn:
            conn.execute(update(grants).filter_by(tenant_id=h.tenant,principal_id=h.principal_id,action="tasks:read").values(scope=dict(h.scope,fields=["private"])) )
        assert h.client.get(f"/api/v1/analysis-tasks/{tid}/report").status_code==404
        assert h.client.get(f"/api/v1/analysis-tasks/{tid}/evidence/{evidence['evidenceId']}").status_code==404
    finally:h.close()


def test_teaching_cancelled_task_never_rereads_source_or_publishes(database,mysql_settings):
    h=TeachingProcessHarness(database,mysql_settings)
    try:
        h.start_api();task,_,_=h.submit();tid=task["taskRef"]["taskId"]
        response=h.client.post(f"/api/v1/analysis-tasks/{tid}/cancel",json=dict(expectedRevision=task["revision"]),headers={"Idempotency-Key":uuid4().hex})
        assert response.status_code==200
        h.start_worker();h.wait_state(tid,"CANCELLED")
        assert h.client.get(f"/api/v1/analysis-tasks/{tid}/report").status_code==404
        assert h.audit_count(tid,"REPORT_PUBLISHED")==h.audit_count(tid,"MODEL_SENT")==0
    finally:h.close()
