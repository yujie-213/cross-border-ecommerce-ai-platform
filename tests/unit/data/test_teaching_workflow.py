"""OFFLINE teaching-source contract fixtures; these do not claim live ERP access."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from commerce_hub.data.projection.observed import project_observations,verify_observations
from commerce_hub.data.quality.observed import capture_observations
from commerce_hub.scenarios.s01_teaching import TeachingS01AdmissionHandler
from tests.support.teaching import observed_fixture


def context(projection):
    return SimpleNamespace(task=dict(scope=projection["scope"],task_id="fixture-task",plan_version=1),
        principal=SimpleNamespace(tenant_id=projection["scope"]["tenantId"]),check=lambda:None)

def test_observed_source_never_uses_engineering_semantics_or_runs_b01(monkeypatch):
    p=observed_fixture();handler=TeachingS01AdmissionHandler(p)
    monkeypatch.setattr("commerce_hub.capabilities.metrics.evaluate",lambda *a,**k:pytest.fail("unadmitted B01 must not run"))
    result=handler.run(context(p),{"packageRef":p["revision"]})
    assert result.sourceNature=="TEACHING_ERP_OBSERVED" and result.completeness=="BLOCKED"
    assert result.dataReport["supplyDemand"]["baseline"] is None and result.dataReport["supplyDemand"]["candidates"]==[]
    assert result.dataReport["scenarioSupplement"]["engineeringFixture"] is False
    assert result.analysisReport["ai"]["status"]=="NOT_ATTEMPTED"
    snapshot=capture_observations(verify_observations(p))
    assert snapshot.manifest["sourceEnvironment"]=="TEACHING_ERP" and snapshot.manifest["acquisitionMethod"]=="NETWORK_READ"
    assert snapshot.manifest["sourceSynthetic"] is True and not snapshot.calculation_allowed

@pytest.mark.parametrize("fault",["unknownField","scope","revision","duplicateDomain","monetary"])
def test_projection_fails_closed_on_raw_data_scope_or_integrity(fault):
    p=observed_fixture()
    if fault=="unknownField":p["domains"][0]["rawResponse"]={"secret":"PRIVATE"}
    elif fault=="scope":p["scope"]["canonicalSkuIds"].append("other")
    elif fault=="revision":p["domains"][1]["measurements"][0]["value"]="999"
    elif fault=="duplicateDomain":p["domains"][1]["domain"]="identity"
    else:p["domains"][1]["measurements"][0].update(field="quote_minimum_amount",unit="SOURCE_CURRENCY_UNCONFIRMED")
    with pytest.raises(ValueError):verify_observations(p)

def test_fixed_package_scope_publication_and_quantity_only_view():
    p=observed_fixture();h=TeachingS01AdmissionHandler(p);ctx=context(p);result=h.run(ctx,{"packageRef":p["revision"]})
    with pytest.raises(ValueError):h.validate({"packageRef":"other"})
    with pytest.raises(ValueError):h.validate_scope({"packageRef":p["revision"]},dict(p["scope"],fields=["private-cost"]))
    report=result.model_dump(mode="json");report.update(taskRef=dict(tenantId=ctx.principal.tenant_id,taskId="fixture-task"),
        reportRef=dict(tenantId=ctx.principal.tenant_id,reportId="fixture-task"),planVersion="1",scenarioId="TEACHING_S01_ADMISSION",scenarioVersion="0.1.0",participants=[])
    view=h.report_view(report)
    assert "observationProjection" not in view["dataReport"] and "manifest" not in view["dataReport"]
    assert view["dataReport"]["evidence"][0]["sourceModuleId"]=="D02"
    report["planVersion"]="2"
    with pytest.raises(ValueError):h.report_view(report)

def test_changed_quantity_cannot_publish_against_original_source_package():
    p=observed_fixture();h=TeachingS01AdmissionHandler(p);result=h.run(context(p),{"packageRef":p["revision"]})
    result.dataReport["observedDomains"][1]["measurements"][0]["value"]="999"
    with pytest.raises(ValueError):h.validate_result(result)


def test_explicit_teaching_assembly_has_no_implicit_file_or_live_model_fallback(monkeypatch):
    from commerce_hub.bootstrap.teaching_erp import registry
    monkeypatch.delenv("COMMERCE_TEACHING_PACKAGE_PATH",raising=False)
    config=SimpleNamespace(environment="test",model_provider="mock",model_network_enabled=False)
    with pytest.raises(ValueError,match="PACKAGE_NOT_AVAILABLE"):registry(config)
    config.model_network_enabled=True
    with pytest.raises(ValueError,match="EXPLICIT_TEST_ENVIRONMENT"):registry(config,observed_fixture())
