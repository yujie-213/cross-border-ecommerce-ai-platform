from datetime import date
from decimal import Decimal

import pytest

from commerce_hub.capabilities.metrics import evaluate
from tests.support.s01 import example, snapshot


def test_known_engineering_target_gap_and_daily_series():
    result = evaluate(snapshot())
    assert result["availableQuantity"] == "55"  # reserved ten was already deducted
    assert result["targetQuantity"] == "90" and result["gapQuantity"] == "15"
    assert [r["closingBalance"] for r in result["series"]] == ["45", "35", "25", "35", "25", "15", "5", "-5", "-15"]
    assert result["firstShortageDate"] == "2026-11-20"
    assert result["metricResultRef"] == evaluate(snapshot())["metricResultRef"]


def test_delayed_supply_preserves_intermediate_shortage_with_candidate():
    value = example()
    value["supply"][0]["availableDate"] = "2026-11-20"
    result = evaluate(snapshot(value), candidate=dict(candidateId="late", quantity=Decimal(20), availableDate=date(2026,11,20)))
    assert result["firstShortageDate"] == "2026-11-18"
    assert result["closingBalance"] == "5" and result["stockoutRisk"]


def test_zero_demand_coverage_is_unknown_not_infinite_or_error():
    value = example()
    for row in value["demand"]:
        row["quantity"] = "0"
    result = evaluate(snapshot(value))
    assert result["coverageDays"] is None and result["gapQuantity"] == "0"


def test_partial_receipt_uses_remaining_once_and_excludes_arrival_after_window():
    value = example()
    value["supply"][0]["remainingQty"] = "7.5"
    assert evaluate(snapshot(value))["inTransitQuantity"] == "7.5"
    value["supply"][0]["availableDate"] = "2027-01-01"
    assert evaluate(snapshot(value))["inTransitQuantity"] == "0"


def test_invalid_data_cannot_reach_calculator():
    value = example()
    value["demand"][0]["quantity"] = None
    with pytest.raises(ValueError, match="DATA_QUALITY_BLOCKED"):
        evaluate(snapshot(value))
