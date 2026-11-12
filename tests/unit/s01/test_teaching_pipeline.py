"""Offline teaching contract consumer tests; no claim of ERP IO."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from commerce_hub.data.admission import AdmissionRejected
from commerce_hub.scenarios.s01_backend import S01BackendHandler, package_ref
from tests.support.admission import build_teaching_admission_package


def prepared():
    package = build_teaching_admission_package()
    entry = dict(kind="TEACHING_SIMULATION", payload=package)
    handler = S01BackendHandler([entry])
    context = SimpleNamespace(
        principal=SimpleNamespace(tenant_id=package["scope"]["tenantId"]),
        task=dict(task_id="offline-teaching-task", plan_version=1, scope=package["scope"]),
        check=lambda: None,
    )
    params = dict(packageRef=package_ref(entry["kind"], package))
    return handler, context, params


def test_teaching_contract_keeps_source_and_public_report_is_cropped():
    handler, context, params = prepared()
    result = handler.run(context, params)
    supply = result.dataReport["supplyDemand"]
    assert result.sourceNature == "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"
    assert supply["baseline"]["gapQuantity"] == "4"
    assert supply["candidates"][0]["quantity"] == "5"
    assert supply["demandMethod"] == "EXPLICIT_TEACHING_DAILY_CURVE"
    assert result.dataReport["scenarioSupplement"]["realAdmission"] == "BLOCKED"
    assert result.dataReport["scenarioSupplement"]["procurementEligible"] is False
    assert result.analysisReport["ai"]["status"] == "NOT_ATTEMPTED"
    report = dict(result.model_dump(mode="json"), taskRef=dict(tenantId=context.principal.tenant_id,
        taskId=context.task["task_id"]), planVersion="1", reportRef=dict(tenantId=context.principal.tenant_id,
        reportId="offline-teaching-report"), scenarioId="S01_BACKEND", scenarioVersion="0.1.0", participants=[])
    public = handler.report_view(report)
    assert public["sourceNature"] == result.sourceNature
    assert not {"sourcePackage", "inputProjection", "manifest"} & set(public["dataReport"])
    assert "test-source-sku" not in str(public)


def test_teaching_publication_cannot_relabel_as_operating_fact():
    handler, context, params = prepared()
    result = handler.run(context, params)
    changed = result.model_copy(update={"sourceNature": "TEACHING_ERP_OBSERVED"})
    with pytest.raises(ValueError):
        handler.validate_publication(changed,
            dict(tenantId=context.principal.tenant_id, taskId=context.task["task_id"]), "1")
    package = deepcopy(next(iter(handler.packages.values()))["payload"])
    with pytest.raises(AdmissionRejected):
        S01BackendHandler([dict(kind="ADMITTED", payload=package)])
