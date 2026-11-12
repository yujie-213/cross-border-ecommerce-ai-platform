from copy import deepcopy
from datetime import timedelta

import pytest

from commerce_hub.data.sync import FixtureConnector, SourceFailure, SourcePage, read_pages
from commerce_hub.data.evidence import resolve
from tests.support.s01 import example, snapshot


def test_fixture_null_and_exact_projection_not_zero():
    value = example()
    value["inventory"][0]["availableQty"] = None
    snap = snapshot(value)
    assert snap.projection.inventory[0].availableQty is None
    assert not snap.calculation_allowed


def test_exact_unit_conversion_and_reserved_stays_informational():
    value = example()
    value["mapping"].update(sourceUnit="CASE", unitsPerSourceUnit="2.5")
    for rows in (value["inventory"], value["demand"], value["supply"]):
        for row in rows:
            row["unit"] = "CASE"
    snap = snapshot(value)
    assert str(snap.projection.inventory[0].availableQty) == "137.5"
    assert str(snap.projection.inventory[0].reservedQty) == "25.0"
    assert snap.calculation_allowed


@pytest.mark.parametrize("mutate,code", [
    (lambda v: v.update(coverageComplete=False), "INCOMPLETE_COVERAGE"),
    (lambda v: v["inventory"][0].update(sku="unknown"), "UNMAPPED_IDENTITY_OR_UNIT"),
    (lambda v: v["inventory"][0].update(availableQty="-1"), "UNKNOWN_OR_NEGATIVE_INVENTORY"),
    (lambda v: v["inventory"][0].update(sourceUpdatedAt="2026-11-10T00:00:00Z"), "STALE_OR_FUTURE_INVENTORY"),
    (lambda v: v["demand"].pop(), "DEMAND_WINDOW_INCOMPLETE_OR_DUPLICATE"),
    (lambda v: v["supply"][0].update(remainingQty=None), "UNKNOWN_OR_NEGATIVE_SUPPLY"),
    (lambda v: v["supply"][0].update(availableDate=None), "UNKNOWN_OR_OVERDUE_AVAILABILITY"),
    (lambda v: v["supply"][0].update(status="UNKNOWN"), "UNKNOWN_SUPPLY_STATUS"),
    (lambda v: v["supply"][0].update(status="RECEIVED"), "CLOSED_SUPPLY_CONFLICT"),
])
def test_quality_fail_closed(mutate, code):
    value = example()
    mutate(value)
    snap = snapshot(value)
    assert not snap.calculation_allowed
    assert code in [i.code for i in snap.issues]


def test_mirror_dedup_conflict_and_ambiguous_inventory():
    value = example()
    value["supply"].append(dict(value["supply"][0], recordId="mirror"))
    snap = snapshot(value)
    assert len(snap.projection.supply) == 1 and snap.calculation_allowed
    value["supply"][1]["remainingQty"] = "100"
    assert not snapshot(value).calculation_allowed
    value = example()
    value["inventory"].append(dict(value["inventory"][0], recordId="other-system"))
    assert not snapshot(value).calculation_allowed


def test_manifest_immutable_versions_replay_and_quality_only_candidate_block():
    value = example()
    first = snapshot(value)
    assert snapshot(deepcopy(value)).snapshotId == first.snapshotId
    value["inventory"][0]["availableQty"] = "56"
    second = snapshot(value)
    assert first.snapshotId != second.snapshotId
    assert first.projection.inventory[0].availableQty == 55
    value["policy"]["qualityDisposition"] = "INVESTIGATE"
    restricted = snapshot(value)
    assert restricted.calculation_allowed and not restricted.candidates_allowed


@pytest.mark.parametrize("change", [
    {"sourceNature": "ERP"}, {"path": ".env"}, {"url": "https://example.invalid"},
    {"policy": {}}, {"asOf": "not-a-date"},
])
def test_no_real_source_or_path_fallback(change):
    with pytest.raises(ValueError):
        FixtureConnector().read(dict(example(), **change))


def test_source_port_bounded_retry_and_no_partial_success():
    class Connector:
        calls = 0
        def read_page(self, cursor):
            self.calls += 1
            if self.calls == 1:
                raise SourceFailure("SOURCE_503")
            return SourcePage(({"id": "1"},), None, True)
    connector = Connector()
    assert read_pages(connector) == ({"id": "1"},) and connector.calls == 2
    class Broken:
        def read_page(self, cursor):
            return SourcePage((), None, False)
    with pytest.raises(SourceFailure, match="INCOMPLETE"):
        read_pages(Broken())
    class Loop:
        def read_page(self, cursor):
            return SourcePage((), "same", False)
    with pytest.raises(SourceFailure, match="CURSOR_LOOP"):
        read_pages(Loop())
    class Forbidden:
        calls = 0
        def read_page(self, cursor):
            self.calls += 1
            raise SourceFailure("SOURCE_403")
    forbidden = Forbidden()
    with pytest.raises(SourceFailure, match="403"):
        read_pages(forbidden)
    assert forbidden.calls == 1


def test_evidence_broken_locator_is_missing():
    assert resolve({"dataReport": {"evidence": [{"evidenceId": "x", "fieldPath": "gone"}]}}, "x") is None


def test_calendar_uses_normalized_utc_and_exact_large_conversion():
    value = example()
    value["asOf"] = "2026-11-12T23:00:00-01:00"
    # This is Nov 13 UTC, so the original demand window must fail closed.
    assert not snapshot(value).calculation_allowed
    value = example()
    value["mapping"].update(sourceUnit="CASE", unitsPerSourceUnit="123456789012.12345678")
    for rows in (value["inventory"], value["demand"], value["supply"]):
        for row in rows:
            row["unit"] = "CASE"
    value["inventory"][0]["availableQty"] = "123456789012.12345678"
    assert str(snapshot(value).projection.inventory[0].availableQty) == "15241578753183967091425.1370442965279684"
    from commerce_hub.data.projection import verify
    assert verify(snapshot(value).projection.model_dump(mode="json")).revision == snapshot(value).projection.revision
