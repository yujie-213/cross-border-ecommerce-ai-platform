from copy import deepcopy
from types import SimpleNamespace

import pytest

from commerce_hub.data.evidence import resolve
from commerce_hub.scenarios.s01 import S01EngineeringHandler
from tests.support.s01 import example


def domain(value=None):
    scope = dict(tenantId="fixture", canonicalSkuIds=["sku-fixture"], storeIds=["store-fixture"],
                 warehouseIds=["warehouse-fixture"], fields=["quantity"])
    return S01EngineeringHandler().run(SimpleNamespace(task={"scope": scope}, check=lambda: None), value or example())


def test_handler_no_ai_and_every_evidence_resolves():
    result = domain()
    assert result.completeness == "RULES_ONLY"
    assert result.analysisReport["ai"]["status"] == "NOT_ATTEMPTED"
    assert result.dataReport["scenarioSupplement"]["realAdmission"] == "BLOCKED"
    for item in result.dataReport["evidence"]:
        assert resolve(result.model_dump(mode="json"), item["evidenceId"]) is not None


@pytest.mark.parametrize("kind", ["snapshot", "version", "metric", "projection", "evidence"])
def test_asset_binding_rejects_conflicts(kind):
    result = domain()
    data = deepcopy(result.dataReport)
    if kind == "snapshot":
        changed = result.model_copy(update={"snapshotRef": "snapshot-wrong"})
    else:
        if kind == "version":
            data["supplyDemand"]["baseline"]["metricVersion"] = "future"
        elif kind == "metric":
            data["supplyDemand"]["baseline"]["gapQuantity"] = "999"
        elif kind == "projection":
            data["inputProjection"]["input"]["policy"]["version"] = "other"
        else:
            data["evidence"][0]["fieldPath"] = "gone"
        changed = result.model_copy(update={"dataReport": data})
    with pytest.raises(ValueError):
        S01EngineeringHandler().validate_result(changed)


def test_blocked_input_produces_quality_report_without_invalid_inventory_evidence():
    value = example()
    value["inventory"] = []
    result = domain(value)
    assert result.completeness == "BLOCKED"
    assert result.dataReport["supplyDemand"]["baseline"] is None
    assert len(result.dataReport["evidence"]) == 1


def persisted(value=None):
    result = domain(value).model_dump(mode="json")
    result.update(taskRef=dict(tenantId="fixture", taskId="task"),
        reportRef=dict(tenantId="fixture", reportId="task"), planVersion="1",
        scenarioId="ENGINEERING_S01", scenarioVersion="0.1.0",
        participants=[dict(scenarioId="ENGINEERING_S01", snapshotRef=result["snapshotRef"])])
    return result


def test_quantity_report_view_omits_raw_assets_and_unrequested_future_fields():
    stored = persisted()
    original = deepcopy(stored)
    stored["dataReport"]["supplyDemand"]["baseline"]["futureCost"] = "PRIVATE_FUTURE_FIELD"
    stored["dataReport"]["supplyDemand"]["baseline"]["series"][0]["customer"] = "PRIVATE_FUTURE_FIELD"
    stored["dataReport"]["supplyDemand"]["candidates"][0]["supplier"] = "PRIVATE_FUTURE_FIELD"
    view = S01EngineeringHandler().report_view(stored)
    assert "inputProjection" not in view["dataReport"] and "manifest" not in view["dataReport"]
    assert "fixtureId" not in view["dataReport"]["scenarioSupplement"]
    assert "PRIVATE_FUTURE_FIELD" not in str(view)
    assert "sourceSku" not in str(view) and "reservedQty" not in str(view)
    assert view["dataReport"]["supplyDemand"] == original["dataReport"]["supplyDemand"]
    assert "inputProjection" in stored["dataReport"]  # No historical asset mutation.
    assert view["dataReport"]["evidence"]
    for item in view["dataReport"]["evidence"]:
        assert item["fieldPath"].startswith("supplyDemand/")
        assert resolve(view, item["evidenceId"]) is not None
    for item in stored["dataReport"]["evidence"]:
        if not item["fieldPath"].startswith("supplyDemand/"):
            assert resolve(view, item["evidenceId"]) is None


@pytest.mark.parametrize("dimension,values", [("fields", ["cost"]),
    ("canonicalSkuIds", ["other"]), ("warehouseIds", ["other"]), ("storeIds", ["other"])])
def test_report_view_rejects_unsupported_field_or_resource_scope(dimension, values):
    report = persisted()
    report["scope"][dimension] = values
    with pytest.raises(ValueError):
        S01EngineeringHandler().report_view(report)


def test_blocked_report_view_preserves_quality_without_raw_record_paths():
    value = example()
    value["inventory"] = []
    report = S01EngineeringHandler().report_view(persisted(value))
    assert report["completeness"] == "BLOCKED"
    assert report["dataReport"]["quality"] and report["dataReport"]["evidence"] == []
    assert all(set(issue) == {"code", "severity", "affects"} for issue in report["dataReport"]["quality"])
