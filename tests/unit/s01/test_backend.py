from copy import deepcopy
from types import SimpleNamespace

import pytest

from commerce_hub.scenarios.s01_backend import S01BackendHandler, package_ref
from tests.support.backend import cases


def context():
    return SimpleNamespace(principal=SimpleNamespace(tenant_id="test-tenant"),
        task=dict(task_id="test-task", plan_version=1, scope=dict(tenantId="test-tenant",
            storeIds=["store-fixture"], warehouseIds=["warehouse-fixture"], canonicalSkuIds=["sku-fixture"], fields=["quantity"])), check=lambda:None)


@pytest.mark.parametrize("case", list("ABCDE"))
def test_five_business_cases_call_existing_calculators_with_fixed_expectations(case):
    entry = cases()[case]
    handler = S01BackendHandler([entry])
    result = handler.run(context(), dict(packageRef=package_ref(entry["kind"], entry["payload"])))
    supply = result.dataReport["supplyDemand"]
    assert result.sourceNature == "SIMULATED_ENGINEERING"
    assert result.dataReport["scenarioSupplement"]["procurementEligible"] is False
    assert result.analysisReport["ai"]["status"] == "NOT_ATTEMPTED"
    if case == "A":
        assert supply["baseline"]["availableQuantity"] == "55"
        assert supply["baseline"]["targetQuantity"] == "90"
        assert supply["baseline"]["gapQuantity"] == "15"
        assert supply["baseline"]["firstShortageDate"] == "2026-11-20"
        assert supply["candidates"][0]["quantity"] == "20"
        assert supply["candidates"][0]["availableDate"] == "2026-11-18"
        assert supply["candidates"][0]["evaluation"]["stockoutRisk"] is False
    elif case == "B":
        assert supply["baseline"]["gapQuantity"] == "0" and supply["candidates"] == []
        assert supply["limitations"] == ["NO_REPLENISHMENT_NEEDED"]
    elif case == "C":
        assert supply["baseline"]["gapQuantity"] == "0"
        assert supply["baseline"]["firstShortageDate"] == "2026-11-13"
        assert supply["baseline"]["stockoutRisk"] is True and supply["candidates"] == []
        assert supply["limitations"] == ["INTERMEDIATE_SHORTAGE_POLICY_UNDEFINED"]
    elif case == "D":
        assert result.completeness == "BLOCKED" and supply["baseline"] is None and supply["candidates"] == []
        assert result.dataReport["reliableFacts"]["inventory"][0]["availableQuantity"] == "55"
    else:
        assert result.completeness == "PARTIAL" and supply["baseline"]["gapQuantity"] == "15" and supply["candidates"] == []
        assert "QUALITY_REQUIRES_RESOLUTION" in {i["code"] for i in result.dataReport["quality"]}


@pytest.mark.parametrize("mutation", ["scope", "quantity", "source", "package", "task", "quality", "reference"])
def test_publication_rejects_valid_shape_tampering(mutation):
    entry = cases()["A"]
    handler = S01BackendHandler([entry])
    result = deepcopy(handler.run(context(), dict(packageRef=package_ref(entry["kind"], entry["payload"]))))
    if mutation == "scope": result.scope["canonicalSkuIds"] = ["outside"]
    elif mutation == "quantity": result.dataReport["supplyDemand"]["candidates"][0]["quantity"] = "21"
    elif mutation == "source": result = result.model_copy(update={"sourceNature":"TEACHING_ERP_OBSERVED"})
    elif mutation == "package": result.dataReport["sourcePackage"]["payload"]["inventory"][0]["availableQty"] = "56"
    elif mutation == "task": result.analysisReport["ai"]["binding"]["taskRef"]["taskId"] = "other"
    elif mutation == "quality": result.dataReport["quality"] = [dict(code="FAKE", severity="INFO", affects="CANDIDATES", path="policy")]
    else: result.dataReport["evidence"][0]["evidenceId"] = "fake"
    with pytest.raises(ValueError):
        handler.validate_publication(result, dict(tenantId="test-tenant", taskId="test-task"), "1")


def test_browser_cannot_supply_paths_rules_or_erp_payloads():
    entry = cases()["A"]
    handler = S01BackendHandler([entry])
    ref = package_ref(entry["kind"], entry["payload"])
    for params in [dict(packageRef=ref, path="file"), dict(packageRef=ref, policy={}), dict(packageRef="missing")]:
        with pytest.raises(ValueError): handler.validate(params)
