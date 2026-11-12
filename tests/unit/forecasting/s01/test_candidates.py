from commerce_hub.capabilities.forecasting import propose
import pytest
from commerce_hub.capabilities.metrics import evaluate
from tests.support.s01 import example, snapshot


def test_each_candidate_uses_identical_b01_and_no_optimality():
    calls = []
    def spy(snap, **kwargs):
        calls.append(kwargs)
        return evaluate(snap, **kwargs)
    result = propose(snapshot(), spy)
    assert len(calls) == 2 and result["selection"] is None
    candidate = result["candidates"][0]
    assert candidate["quantity"] == "20" and not candidate["procurementEligible"]
    assert candidate["evaluation"]["closingBalance"] == "5"
    assert candidate["evaluation"]["snapshotRef"] == result["baseline"]["snapshotRef"]


def test_moq_multiple_independent_and_hard_cap_no_solution():
    value = example()
    value["policy"].update(moq="21", orderMultiple="8")
    assert propose(snapshot(value))["candidates"][0]["quantity"] == "24"
    value["policy"]["maxOrderQty"] = "23"
    assert propose(snapshot(value))["limitations"] == ["NO_FEASIBLE_QUANTITY"]


def test_missing_constraints_only_baseline_and_quality_cannot_be_overridden():
    for field, val in [("moq", None), ("orderMultiple", "0"), ("maxOrderQty", None), ("qualityDisposition", "UNKNOWN")]:
        value = example()
        value["policy"][field] = val
        result = propose(snapshot(value))
        assert result["baseline"] is not None and not result["candidates"]
    value = example()
    value["inventory"][0]["availableQty"] = None
    assert propose(snapshot(value))["baseline"] is None


@pytest.mark.parametrize("zero_demand", [False, True])
def test_zero_gap_without_shortage_has_no_zero_piece_candidate(zero_demand):
    value = example()
    if zero_demand:
        for row in value["demand"]:
            row["quantity"] = "0"
    else:
        value["supply"][0]["remainingQty"] = "35"
    calls = []
    def spy(snap, **kwargs):
        calls.append(kwargs)
        return evaluate(snap, **kwargs)
    result = propose(snapshot(value), spy)
    assert result["baseline"]["gapQuantity"] == "0"
    assert not result["baseline"]["stockoutRisk"]
    assert result["candidates"] == [] and result["selection"] is None
    assert result["limitations"] == ["NO_REPLENISHMENT_NEEDED"]
    assert calls == [{}]  # Only B01 establishes the absence of shortage.


@pytest.mark.parametrize("remaining", ["35", "100"])
def test_zero_gap_with_intermediate_shortage_requires_missing_policy(remaining):
    value = example()
    value["supply"][0].update(remainingQty=remaining, availableDate="2026-11-21")
    result = propose(snapshot(value))
    assert result["baseline"]["gapQuantity"] == "0"
    assert result["baseline"]["stockoutRisk"]
    assert result["baseline"]["firstShortageDate"] == "2026-11-18"
    assert result["candidates"] == []
    assert result["limitations"] == ["INTERMEDIATE_SHORTAGE_POLICY_UNDEFINED"]


@pytest.mark.parametrize("field,value", [("moq", None), ("maxOrderQty", "0"),
    ("orderMultiple", None), ("candidateDates", ["2026-11-12"]),
    ("candidateDates", ["2026-11-22"])])
def test_zero_total_gap_does_not_override_missing_constraints(field, value):
    sample = example()
    sample["supply"][0].update(remainingQty="35", availableDate="2026-11-21")
    sample["policy"][field] = value
    result = propose(snapshot(sample))
    assert result["baseline"]["stockoutRisk"] and result["baseline"]["gapQuantity"] == "0"
    assert result["candidates"] == []
    assert result["limitations"] == ["CANDIDATE_RULES_OR_QUALITY_BLOCKED"]


def test_positive_gap_candidate_dates_remain_bounded_and_risk_is_evaluated_by_b01():
    value = example()
    value["policy"]["candidateDates"] = ["2026-11-21", "2026-11-18", "2026-11-18"]
    result = propose(snapshot(value))
    assert [c["availableDate"] for c in result["candidates"]] == ["2026-11-18", "2026-11-21"]
    assert [c["quantity"] for c in result["candidates"]] == ["20", "20"]
    assert not result["candidates"][0]["evaluation"]["stockoutRisk"]
    assert result["candidates"][1]["evaluation"]["stockoutRisk"]
