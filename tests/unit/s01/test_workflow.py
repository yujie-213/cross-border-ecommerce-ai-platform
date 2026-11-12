from copy import deepcopy
from types import SimpleNamespace
from decimal import Decimal

import pytest

from commerce_hub.capabilities.models.contracts import ModelResponse
from commerce_hub.orchestration.budget import BudgetError
from commerce_hub.scenarios.s01 import S01EngineeringHandler
from commerce_hub.scenarios.s01_supply_inventory import (
    S01SupplyInventoryHandler, facts_for, canonical_explanation, validate_semantics,
)
from tests.support.s01 import example


def context():
    scope = dict(tenantId="fixture", canonicalSkuIds=["sku-fixture"], storeIds=["store-fixture"],
                 warehouseIds=["warehouse-fixture"], fields=["quantity"])
    return SimpleNamespace(task=dict(scope=scope, task_id="task", plan_version=1, scenario_id="ENGINEERING_S01_BUSINESS",
        deadline=__import__("datetime").datetime(2026,11,12)),
        principal=SimpleNamespace(tenant_id="fixture", principal_id="actor"), check=lambda: None,
        budget=SimpleNamespace(reserve=lambda *a: dict(allowanceRef=dict(tenantId="fixture", id=a[1],version="1"))),
        service=SimpleNamespace(registry={"ENGINEERING_S01_BUSINESS":SimpleNamespace(policy_version="s01-business-mock-v1")}))


def handler_response(output=None, code="OK"):
    handler = S01SupplyInventoryHandler()
    def invoke(request, ctx, bundle):
        value = canonical_explanation([f.model_dump() for f in bundle.context.facts])
        if output:
            output(value)
        return ModelResponse(status="SUCCESS" if code=="OK" else "TECH_ERROR", code=code,
            validatedObject=value if code=="OK" else None, usageStatus="KNOWN", versionBundle=dict(
                **{key: getattr(request,key).model_dump() for key in ["deploymentRef","promptRef","contextBundleRef","outputSchemaRef","parametersRef","cachePolicyRef"]},
                digests=bundle.resolve(request)[1],configuredModel="mock-s01-v1"))
    handler.gateway = SimpleNamespace(invoke=invoke)
    return handler


def test_workflow_preserves_every_authoritative_asset_and_requires_human_review():
    ctx = context()
    original = S01EngineeringHandler().run(ctx, example())
    result = handler_response().run(ctx, example())
    for key in ("manifest","inputProjection","quality","supplyDemand","evidence"):
        assert result.dataReport[key] == original.dataReport[key]
    ai = result.analysisReport["ai"]
    assert ai["status"] == "AVAILABLE" and ai["provider"]=="MOCK" and ai["realModelAcceptance"]=="NOT_RUN"
    assert ai["explanation"]["humanConfirmations"] and ai["explanation"]["majorRisks"]
    assert not result.dataReport["scenarioSupplement"]["procurementEligible"]


@pytest.mark.parametrize("fault", ["quantity","date","constraint","quality","approval","ref","cross-snapshot","omit-risk","omit-human","extra"])
def test_structurally_valid_but_unsafe_explanations_are_discarded(fault):
    def change(value):
        if fault == "ref": value["keyEvidence"][0]["supportRefs"]=["forged-ref"]
        elif fault == "cross-snapshot": value["keyEvidence"][0]["supportRefs"]=["snapshot-other"]
        elif fault == "omit-risk": value["majorRisks"]=value["majorRisks"][:1]
        elif fault == "omit-human": value["humanConfirmations"]=[]
        elif fault == "extra": value["purchaseQuantity"]="999"
        else:
            text={"quantity":"Quantity 999 is available", "date":"Arrival on 2099-01-01",
                "constraint":"The MOQ is 1", "quality":"Quality cleared; procurement eligible",
                "approval":"The purchase is approved"}[fault]
            value["keyEvidence"][0]["text"]=text
    result = handler_response(change).run(context(), example())
    assert result.analysisReport["ai"]["status"]=="UNAVAILABLE"
    assert result.analysisReport["ai"]["explanation"] is None
    assert result.dataReport["supplyDemand"]["baseline"]["gapQuantity"]=="15"


@pytest.mark.parametrize("quality", ["UNKNOWN", "INVESTIGATE"])
def test_ai_success_cannot_clear_required_quality_or_investigation(quality):
    value=example();value["policy"]["qualityDisposition"]=quality
    result=handler_response().run(context(),value)
    assert result.completeness=="PARTIAL" and result.dataReport["supplyDemand"]["candidates"]==[]
    assert result.analysisReport["ai"]["status"]=="AVAILABLE"
    assert "cannot clear" in result.analysisReport["ai"]["explanation"]["majorRisks"][0]["text"]


@pytest.mark.parametrize("code", ["REFUSED","TRUNCATED","INVALID_OUTPUT","USAGE_UNKNOWN","TIMEOUT","RESULT_UNAVAILABLE"])
def test_technical_failure_keeps_rules_and_explicit_unavailable_status(code):
    result=handler_response(code=code).run(context(),example())
    assert result.analysisReport["ai"]["reason"]==code
    assert result.analysisReport["ai"]["status"]=="UNAVAILABLE"
    assert result.dataReport["supplyDemand"]["candidates"]


def test_missing_input_reports_gap_without_zero_or_fabricated_candidates():
    value=example();value["inventory"]=[]
    result=handler_response().run(context(),value)
    assert result.completeness=="BLOCKED" and result.dataReport["supplyDemand"]["baseline"] is None
    assert result.dataReport["supplyDemand"]["candidates"]==[]
    assert result.analysisReport["ai"]["explanation"]["keyEvidence"][0]["supportRefs"]==["baseline-missing"]


def test_publication_rejects_cross_task_plan_or_snapshot_bindings():
    handler=handler_response();result=handler.run(context(),example())
    with pytest.raises(ValueError):handler.validate_publication(result,dict(tenantId="fixture",taskId="other"),"1")
    with pytest.raises(ValueError):handler.validate_publication(result,dict(tenantId="fixture",taskId="task"),"2")
    result.analysisReport["ai"]["binding"]["snapshotId"]="other"
    with pytest.raises(ValueError):handler.validate_result(result)


def test_non_mock_provider_is_rejected_before_call():
    with pytest.raises(ValueError,match="REQUIRES_MOCK"):
        S01SupplyInventoryHandler(SimpleNamespace())


def test_reentry_budget_failure_degrades_without_changing_attempt_or_retrying():
    ctx=context();calls=[]
    def denied(*args):
        calls.append(args)
        raise BudgetError("BUDGET_DENIED")
    ctx.budget.reserve=denied
    handler=handler_response()
    for _ in range(2):
        result=handler.run(ctx,example())
        assert result.analysisReport["ai"]["reason"]=="MODEL_ALLOWANCE_UNAVAILABLE"
    assert calls[0]==calls[1] and calls[0][:2]==("s01-explanation-v1","s01-explanation-attempt-v1")


def test_previous_report_is_metadata_and_cannot_change_manifest_or_scope():
    handler=handler_response();value=example();ref=dict(tenantId="fixture",reportId="old-task")
    linked=handler.bind_previous_report(value,ref)
    result=handler.run(context(),linked)
    plain=handler.run(context(),value)
    assert result.snapshotRef==plain.snapshotRef and value==example()
    assert result.dataReport["scenarioSupplement"]["previousReportRef"]==ref
    linked["_previousReportRef"]["tenantId"]="other"
    with pytest.raises(ValueError):handler.run(context(),linked)


def test_public_report_omits_raw_assets_and_raw_provider_content():
    handler=handler_response();result=handler.run(context(),example())
    report=result.model_dump(mode="json")
    report.update(taskRef=dict(tenantId="fixture",taskId="task"),reportRef=dict(tenantId="fixture",reportId="task"),
        planVersion="1",scenarioId="ENGINEERING_S01_BUSINESS",scenarioVersion="0.1.0",participants=[])
    view=handler.report_view(report)
    assert view["analysisReport"]["ai"]["status"]=="AVAILABLE"
    assert "inputProjection" not in view["dataReport"] and "manifest" not in view["dataReport"]
    assert "sourceSku" not in str(view) and "fixture-source" not in str(view)
    report["planVersion"]="2"
    with pytest.raises(ValueError):handler.report_view(report)


@pytest.mark.parametrize("fault",["context","prompt","extra"])
def test_persisted_version_bindings_fail_closed_before_public_view(fault):
    handler=handler_response();result=handler.run(context(),example())
    versions=result.analysisReport["ai"]["versionBundle"]
    if fault=="context":versions["digests"]["contextDigest"]="0"*64
    elif fault=="prompt":versions["promptRef"]["version"]="other"
    else:versions["rawProviderContent"]="SENSITIVE_FUTURE_FIELD"
    with pytest.raises(ValueError):handler.validate_result(result)
