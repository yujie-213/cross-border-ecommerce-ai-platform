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
