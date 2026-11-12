from datetime import datetime, timezone
import shutil
from types import SimpleNamespace

from tools.s01_candidate_discovery import (
    NEGATIVE_SKU,
    assess_candidate,
    choose_for_verification,
    discover_candidates,
    run_discovery,
)


class FakeReader:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        self.events = []

    def _batch(self, path, parameters):
        self.calls.append((path, dict(parameters or {})))
        key = (path, tuple(sorted((name, repr(value)) for name, value in (parameters or {}).items())))
        value = self.responses.get(key, self.responses.get(path, []))
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(records=tuple(value), complete=True, total=len(value),
                               observed_at="2026-11-12T00:00:00+00:00", fingerprint="f" + str(len(self.calls)))

    def discover(self, path, parameters=None, page_size=20):
        return self._batch(path, parameters)

    def read(self, path, parameters=None, **_):
        return self._batch(path, parameters)


def row(sku, n=1):
    return dict(id=n, sku=sku, tenant_id="t", store_id=1, store_name="s", wid=2,
                warehouse_name="w", available=4, updated_at="2026-11-11T00:00:00Z")


def test_candidate_discovery_is_bounded_and_retains_negative_control():
    skus = [f"SKU-{i}" for i in range(25)]
    reader = FakeReader({"/api/v1/inventory": [row(s, i) for i, s in enumerate(skus)],
                         "/api/v1/listings": [dict(row(s, i), listing_id=i) for i, s in enumerate(skus)],
                         "/api/v1/products": [dict(row(s, i), moq=1, default_carton_qty=1) for i, s in enumerate(skus)]})
    candidates, _ = discover_candidates(reader, limit=20)
    assert len(candidates) == 20
    assert NEGATIVE_SKU in {x["sku"] for x in candidates}
    chosen = choose_for_verification(candidates, count=5)
    assert 3 <= len(chosen) <= 5 and NEGATIVE_SKU in {x["sku"] for x in chosen}


def test_global_failure_is_not_retried_per_candidate(monkeypatch):
    import tools.s01_candidate_discovery as module
    reader = FakeReader({})
    candidates = [dict(sku=f"S{i}", inventory=[], listings=[], products=[]) for i in range(4)]
    candidates.append(dict(sku=NEGATIVE_SKU, inventory=[], listings=[], products=[]))
    monkeypatch.setattr(module, "discover_candidates", lambda *_a, **_k: (candidates, {}))
    monkeypatch.setattr(module, "check_global_endpoints", lambda _r: {
        "demand": module.Capture("sales", [], None, None, None, None, "ERP_503"),
        "supply": module.Capture("purchases", [], None, None, None, None, "ERP_503")})
    public, _ = run_discovery(reader, verify_count=5, now=datetime(2026, 11, 12, tzinfo=timezone.utc))
    assert not [x for x in reader.calls if x[0] in {"/api/v1/sales-orders", "/api/v1/purchase-orders"}]
    negative_id = next(x["candidateId"] for x in public["candidates"] if x["knownNegativeControl"])
    assert public["recommendation"]["candidateId"] != negative_id
    assert negative_id not in public["recommendation"]["tiedCandidateIds"]


def test_candidate_verification_scopes_inventory_to_one_store_and_warehouse():
    import tools.s01_candidate_discovery as module
    candidate = dict(sku="S1", inventory=[row("S1")], listings=[], products=[])
    reader = FakeReader({})
    health = {name: module.Capture(name, [], True, 0, "2026-11-12T00:00:00+00:00", "fp")
              for name in ("demand", "supply")}
    module._capture_candidate(reader, candidate, health, datetime(2026, 11, 12, tzinfo=timezone.utc))
    inventory_call = next(parameters for path, parameters in reader.calls if path == "/api/v1/inventory")
    assert inventory_call["store_id"] == 1 and inventory_call["wid"] == 2


def test_empty_records_are_unknown_not_zero():
    import tools.s01_candidate_discovery as module
    empty = module.Capture("x", [], True, 0, "2026-11-12T00:00:00+00:00", "fp")
    captures = {name: empty for name in ("inventory", "product", "listing", "quotes", "stores", "warehouses",
                                                  "buckets", "sales", "purchases", "inbound", "voice")}
    result = assess_candidate(dict(sku="PRIVATE", inventory=[], listings=[], products=[]), captures)
    assert "NO_RECORDS_NOT_ZERO" in result["exactGaps"]
    assert "NO_MATCHING_LINES_NOT_ZERO" in result["exactGaps"]
    assert result["computability"] == "BLOCKED"


def test_public_assessment_has_aliases_and_no_source_identifier_values():
    import tools.s01_candidate_discovery as module
    sku = "SECRET-SKU"
    inventory = module.Capture("inventory", [row(sku)], True, 1, "2026-11-12T00:00:00+00:00", "fp")
    product = module.Capture("product", [dict(row(sku), moq=12, default_carton_qty=6,
                                               procurement_lead_days=5, qc_standard="A")], True, 1,
                             "2026-11-12T00:00:00+00:00", "fp2")
    listing = module.Capture("listing", [dict(row(sku), listing_id="PRIVATE-ID")], True, 1,
                             "2026-11-12T00:00:00+00:00", "fp3")
    empty = module.Capture("x", [], True, 0, "2026-11-12T00:00:00+00:00", "fp4")
    captures = dict(inventory=inventory, product=product, listing=listing, quotes=empty, stores=empty,
                    warehouses=empty, buckets=empty, sales=empty, purchases=empty, inbound=empty, voice=empty)
    result = assess_candidate(dict(sku=sku, inventory=[], listings=[], products=[]), captures)
    rendered = str(result)
    assert result["candidateId"].startswith("sku-")
    assert sku not in rendered and "PRIVATE-ID" not in rendered


def test_fixed_private_candidate_builds_quantity_only_blocked_observation():
    import json
    import tools.s01_candidate_discovery as module
    from commerce_hub.data.projection.observed import verify_observations
    from commerce_hub.data.quality.observed import capture_observations
    test_root = module.PRIVATE_ROOT / "unit-test-build-observation"
    if test_root.exists():
        shutil.rmtree(test_root)
    run = test_root / "run-one"
    run.mkdir(parents=True)
    sku = "SECRET-SKU"
    def cap(rows, fingerprint, *, error=None):
        return dict(rows=rows, complete=None if error else True, total=None if error else len(rows),
                    observedAt="2026-11-12T00:00:00+00:00", fingerprint=fingerprint, error=error)
    inventory = [dict(row(sku), quantity=9, synthetic=True, order_sn="PRIVATE-ORDER")]
    product = [dict(row(sku), synthetic=True, moq=12, default_carton_qty=6,
                    procurement_lead_days=5, qc_standard="A", cost=999, price=1000)]
    captures = {
        "inventory": cap(inventory, "1" * 64), "product": cap(product, "2" * 64),
        "listing": cap([dict(row(sku), listing_id="PRIVATE-LISTING")], "3" * 64),
        "stores": cap([dict(id=1)], "4" * 64), "warehouses": cap([dict(id=2)], "5" * 64),
        "quotes": cap([dict(minimum_quantity=12, minimum_amount=999, unit_price=88)], "6" * 64),
        "buckets": cap([], "7" * 64), "sales": cap([], "8" * 64, error="ERP_503"),
        "purchases": cap([dict(order_sn="PRIVATE-PO", amount=1000, item_list=[])], "9" * 64),
        "inbound": cap([], "a" * 64), "voice": cap([], "b" * 64),
    }
    private_path = run / "discovery-private.json"
    private_path.write_text(json.dumps({"candidates": [{"sku": sku, "captures": captures}]}), encoding="utf-8")
    try:
        projection = module.build_best_observation(private_path, tenant_id="tenant-test")
        rendered = json.dumps(projection)
        assert projection["scope"]["fields"] == ["quantity"] and projection["ownerConfirmed"] is False
        assert projection["sourceSynthetic"] is True and projection["revalidationFailed"] is True
        assert all(value not in rendered for value in [sku, "PRIVATE-ORDER", "PRIVATE-LISTING", "PRIVATE-PO",
                                                         "minimum_amount", "unit_price", '"cost"', '"price"'])
        snapshot = capture_observations(verify_observations(projection))
        assert snapshot.calculation_allowed is False and snapshot.candidates_allowed is False
        assert "PILOT_IDENTITY_NOT_CONFIRMED" in {issue.code for issue in snapshot.issues}
    finally:
        shutil.rmtree(test_root)
