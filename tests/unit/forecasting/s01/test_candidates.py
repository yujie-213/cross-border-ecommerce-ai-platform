from commerce_hub.capabilities.forecasting import propose
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
