"""TEST_ONLY contract shape reaches existing calculators, never real admission."""
import pytest

from commerce_hub.data.admission import normalize, AdmissionRejected
from commerce_hub.data.contracts import AdmittedInput
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture
from commerce_hub.capabilities.forecasting import propose
from commerce_hub.scenarios.s01_backend import S01BackendHandler
from tests.support.admission import build_test_only_admission_package


def test_admitted_contract_uses_original_calculation_and_is_default_disabled():
    package = build_test_only_admission_package(admittable_shape=True)
    with pytest.raises(AdmissionRejected):
        normalize(package)
    with pytest.raises(AdmissionRejected):
        S01BackendHandler([dict(kind="ADMITTED", payload=package)])
    value = AdmittedInput.model_validate(normalize(package, allow_test_only=True))
    snapshot = capture(project(value, "test-only-admission-contract"))
    result = propose(snapshot)
    assert snapshot.calculation_allowed and snapshot.candidates_allowed
    assert result["baseline"]["gapQuantity"] == "4"
    assert result["candidates"][0]["quantity"] == "5"
    assert result["candidates"][0]["procurementEligible"] is False
    assert result["candidates"][0]["evaluation"]["stockoutRisk"] is False
