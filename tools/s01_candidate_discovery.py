"""Bounded TEACHING_ERP_ONLY candidate discovery for the S01 backend closure.

Raw records, source identifiers and query values are written only below the
git-ignored private directory.  The committed report contains aliases,
coverage states, gap codes and response fingerprints; it is never an admitted
calculation package.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import dotenv_values

from commerce_hub.adapters.erp import (
    AUTH_PATH,
    ERPConfig,
    ERPError,
    TeachingERPReader,
    https_transport,
)


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT / "data/private/s01-backend-erp-discovery"
PUBLIC_ROOT = ROOT / "docs/evidence/S01-BACKEND/erp"
NEGATIVE_SKU = "SKT-OL-XXL"
MAX_CANDIDATES = 20
MAX_VERIFIED = 5


def _alias(kind: str, value: object) -> str:
    digest = hashlib.sha256(str(value).encode()).hexdigest()[:20]
    return f"{kind}-{digest}"


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n").encode()


@dataclass
class Capture:
    name: str
    rows: list[dict[str, Any]]
    complete: bool | None
    total: int | None
    observed_at: str | None
    fingerprint: str | None
    error: str | None = None

    def private(self) -> dict[str, Any]:
        return dict(name=self.name, rows=self.rows, complete=self.complete, total=self.total,
                    observedAt=self.observed_at, fingerprint=self.fingerprint, error=self.error)


def _read(reader: TeachingERPReader, name: str, path: str, parameters: dict[str, Any] | None = None,
          *, method: str = "GET", discover: bool = False, page_size: int = 20,
          max_pages: int = 5) -> Capture:
    try:
        batch = (reader.discover(path, parameters, page_size=page_size) if discover else
                 reader.read(path, parameters, method=method, page_size=page_size, max_pages=max_pages))
        return Capture(name, list(batch.records), batch.complete, batch.total,
                       batch.observed_at, batch.fingerprint)
    except ERPError as error:
        return Capture(name, [], None, None, None, None, error.code)


def check_global_endpoints(reader: TeachingERPReader) -> dict[str, Capture]:
    """Probe each high-value global endpoint once before candidate expansion."""
    return {
        "demand": _read(reader, "global_sales", "/api/v1/sales-orders", discover=True, page_size=1),
        "supply": _read(reader, "global_purchases", "/api/v1/purchase-orders", discover=True, page_size=1),
    }


def discover_candidates(reader: TeachingERPReader, *, limit: int = MAX_CANDIDATES) -> tuple[list[dict[str, Any]], dict[str, Capture]]:
    if type(limit) is not int or not 1 <= limit <= MAX_CANDIDATES:
        raise ValueError("CANDIDATE_LIMIT_REJECTED")
    captures = {
        "inventory": _read(reader, "candidate_inventory", "/api/v1/inventory", discover=True, page_size=limit),
        "listings": _read(reader, "candidate_listings", "/api/v1/listings", discover=True, page_size=limit),
        "products": _read(reader, "candidate_products", "/api/v1/products", discover=True, page_size=limit),
    }
    by_sku: dict[str, dict[str, Any]] = {}
    for domain in ("inventory", "listings", "products"):
        for row in captures[domain].rows:
            sku = row.get("sku")
            if not isinstance(sku, str) or not sku.strip():
                continue
            item = by_sku.setdefault(sku, {"sku": sku, "inventory": [], "listings": [], "products": []})
            item[domain].append(row)
    # Keep the known incomplete sample as an explicit negative control.
    by_sku.setdefault(NEGATIVE_SKU, {"sku": NEGATIVE_SKU, "inventory": [], "listings": [], "products": []})
    ranked = sorted(by_sku.values(), key=_discovery_rank, reverse=True)
    selected = ranked[:limit]
    if NEGATIVE_SKU not in {x["sku"] for x in selected}:
        selected[-1] = by_sku[NEGATIVE_SKU]
    return selected, captures


def _latest(rows: list[dict[str, Any]]) -> str:
    values = [str(r.get("updated_at") or r.get("created_at") or "") for r in rows]
    return max(values, default="")


def _discovery_rank(candidate: dict[str, Any]) -> tuple[int, int, int, str]:
    inventory, listings, products = candidate["inventory"], candidate["listings"], candidate["products"]
    linked = bool(inventory and listings and products)
    quantities = sum(row.get("available") is not None for row in inventory)
    constraints = sum(row.get(key) is not None for row in products for key in ("moq", "default_carton_qty", "procurement_lead_days"))
    return (int(linked), quantities + constraints, len(inventory) + len(listings), _latest(inventory + listings + products))


def choose_for_verification(candidates: list[dict[str, Any]], *, count: int = MAX_VERIFIED) -> list[dict[str, Any]]:
    if type(count) is not int or not 3 <= count <= MAX_VERIFIED:
        raise ValueError("VERIFICATION_COUNT_REJECTED")
    chosen = sorted(candidates, key=_discovery_rank, reverse=True)[:min(count, len(candidates))]
    negative = next((x for x in candidates if x["sku"] == NEGATIVE_SKU), None)
    if negative and negative not in chosen:
        chosen[-1] = negative
    return chosen


def _capture_candidate(reader: TeachingERPReader, candidate: dict[str, Any], global_health: dict[str, Capture],
                       today: datetime) -> dict[str, Capture]:
    sku = candidate["sku"]
    seed = next((x for x in candidate["inventory"] if x.get("wid") is not None and x.get("store_id") is not None), {})
    inventory_parameters = dict(field="sku", q=sku, match="exact")
    if seed:
        inventory_parameters.update(wid=seed["wid"], store_id=seed["store_id"])
    listing_parameters = dict(field="sku", q=sku, match="exact")
    if seed.get("store_name"):
        listing_parameters["store_name"] = seed["store_name"]
    captures: dict[str, Capture] = {
        "inventory": _read(reader, "inventory", "/api/v1/inventory", inventory_parameters),
        "product": _read(reader, "product", "/api/v1/products", dict(field="sku", q=sku, match="exact")),
        "listing": _read(reader, "listing", "/api/v1/listings", listing_parameters),
        "quotes": _read(reader, "quotes", "/api/v1/supplier-quotes", dict(sku=sku)),
    }
    inventories = captures["inventory"].rows
    listings = captures["listing"].rows
    store_ids = sorted({str(x["store_id"]) for x in inventories if x.get("store_id") is not None})
    warehouse_ids = sorted({str(x["wid"]) for x in inventories if x.get("wid") is not None})
    store_names = sorted({str(x["store_name"]) for x in listings if x.get("store_name")})
    warehouse_names = sorted({str(x["warehouse_name"]) for x in inventories if x.get("warehouse_name")})
    captures["stores"] = (_read(reader, "stores", "/api/v1/store-authorizations", {"ids": store_ids})
                          if store_ids else Capture("stores", [], None, None, None, None, "IDENTITY_SCOPE_UNKNOWN"))
    captures["warehouses"] = (_read(reader, "warehouses", "/api/v1/warehouses", {"ids": warehouse_ids})
                              if warehouse_ids else Capture("warehouses", [], None, None, None, None, "IDENTITY_SCOPE_UNKNOWN"))
    captures["buckets"] = (_read(reader, "buckets", "/erp/sc/routing/data/local_inventory/inventoryDetails",
                                {"wid": warehouse_ids[0], "sku": sku}, method="POST")
                           if len(warehouse_ids) == 1 else Capture("buckets", [], None, None, None, None, "WAREHOUSE_NOT_EXACT"))
    if global_health["demand"].error:
        captures["sales"] = Capture("sales", [], None, None, None, None,
                                    "GLOBAL_ENDPOINT_" + global_health["demand"].error)
    elif len(store_names) == 1 and len(warehouse_names) == 1:
        captures["sales"] = _read(reader, "sales", "/api/v1/sales-orders",
                                  {"store_name": store_names[0], "shipping_warehouse": warehouse_names[0]})
    else:
        captures["sales"] = Capture("sales", [], None, None, None, None, "IDENTITY_SCOPE_UNKNOWN")
    if global_health["supply"].error:
        captures["purchases"] = Capture("purchases", [], None, None, None, None,
                                        "GLOBAL_ENDPOINT_" + global_health["supply"].error)
    elif len(warehouse_names) == 1:
        captures["purchases"] = _read(reader, "purchases", "/api/v1/purchase-orders",
                                      {"field": "warehouse_name", "q": warehouse_names[0], "match": "exact"})
    else:
        captures["purchases"] = Capture("purchases", [], None, None, None, None, "IDENTITY_SCOPE_UNKNOWN")
    start = (today - timedelta(days=30)).date().isoformat()
    end = today.date().isoformat()
    captures["inbound"] = (_read(reader, "inbound", "/api/v1/inbound-orders",
                                 {"warehouse_name": warehouse_names[0], "date_from": start, "date_to": end})
                           if len(warehouse_names) == 1 else Capture("inbound", [], None, None, None, None, "IDENTITY_SCOPE_UNKNOWN"))
    captures["voice"] = (_read(reader, "voice", "/api/v1/customer-voice",
                               {"store_id": store_ids[0], "kind": "reviews", "date_from": start, "date_to": end})
                         if len(store_ids) == 1 else Capture("voice", [], None, None, None, None, "IDENTITY_SCOPE_UNKNOWN"))
    return captures


def _items_for_sku(rows: list[dict[str, Any]], sku: str) -> list[dict[str, Any]]:
    found = []
    for row in rows:
        if row.get("sku") == sku:
            found.append(row)
        items = row.get("item_list")
        if isinstance(items, list):
            found.extend(x for x in items if isinstance(x, dict) and x.get("sku") == sku)
    return found


def _state(observed: bool, capture: Capture, *, partial: bool = False) -> str:
    if capture.error:
        return "ERROR"
    if not observed:
        return "UNKNOWN"
    return "PARTIAL" if partial or capture.complete is not True else "OBSERVED"


def assess_candidate(candidate: dict[str, Any], captures: dict[str, Capture]) -> dict[str, Any]:
    sku = candidate["sku"]
    inv, product, listing = captures["inventory"], captures["product"], captures["listing"]
    products = [x for x in product.rows if x.get("sku") == sku]
    listings = [x for x in listing.rows if x.get("sku") == sku]
    inventories = [x for x in inv.rows if x.get("sku") == sku]
    sales = _items_for_sku(captures["sales"].rows, sku)
    purchases = _items_for_sku(captures["purchases"].rows, sku)
    gaps: dict[str, list[str]] = defaultdict(list)
    tenants = {str(x.get("tenant_id")) for x in inventories + products + listings if x.get("tenant_id") is not None}
    stores, warehouses = captures["stores"].rows, captures["warehouses"].rows
    store_ids = {str(x.get("store_id")) for x in inventories if x.get("store_id") is not None}
    warehouse_ids = {str(x.get("wid")) for x in inventories if x.get("wid") is not None}
    identity_ok = bool(inventories and len(products) == 1 and listings and len(tenants) == 1
                       and len(store_ids) == 1 and len(warehouse_ids) == 1
                       and {str(x.get("id")) for x in stores} == store_ids
                       and {str(x.get("id")) for x in warehouses} == warehouse_ids)
    if not identity_ok: gaps["identity"].append("SKU_STORE_WAREHOUSE_LISTING_MAPPING_INCOMPLETE")
    inventory_ok = bool(inventories and all(x.get("available") is not None and x.get("updated_at") for x in inventories))
    if not inventory_ok: gaps["inventory"].append("AVAILABLE_OR_SOURCE_TIME_MISSING")
    if inventories: gaps["inventory"].extend(["NET_AVAILABLE_SEMANTICS_UNSIGNED", "BATCH_AGGREGATION_UNSIGNED", "FRESHNESS_THRESHOLD_UNSIGNED"])
    if captures["sales"].error: gaps["demand"].append(captures["sales"].error)
    elif not sales: gaps["demand"].append("NO_RECORDS_NOT_ZERO")
    gaps["demand"].append("HISTORY_TO_FUTURE_RULE_UNSIGNED")
    if captures["purchases"].error: gaps["supply"].append(captures["purchases"].error)
    elif not purchases: gaps["supply"].append("NO_MATCHING_LINES_NOT_ZERO")
    gaps["supply"].append("UNRECEIVED_DEDUP_RULE_UNSIGNED")
    availability = [x for x in purchases if x.get("planned_arrival") or x.get("available_date")]
    if not availability: gaps["availability"].append("SELLABLE_DATE_MISSING")
    if products and products[0].get("procurement_lead_days") is None: gaps["availability"].append("LEAD_TIME_MISSING")
    quotes = captures["quotes"].rows
    moq = bool(products and products[0].get("moq") is not None or any(x.get("minimum_quantity") is not None for x in quotes))
    if not moq: gaps["moq"].append("MOQ_MISSING")
    if len({str(x.get("moq")) for x in products if x.get("moq") is not None} |
           {str(x.get("minimum_quantity")) for x in quotes if x.get("minimum_quantity") is not None}) > 1:
        gaps["moq"].append("MOQ_CONFLICT_REQUIRES_RULE")
    multiple = bool(products and products[0].get("default_carton_qty") is not None)
    if not multiple: gaps["orderMultiple"].append("ORDER_MULTIPLE_MISSING")
    else: gaps["orderMultiple"].append("CARTON_QUANTITY_SEMANTICS_UNSIGNED")
    quality_signal = bool(products and products[0].get("qc_standard") or captures["voice"].rows or captures["inbound"].rows)
    if not quality_signal: gaps["quality"].append("QUALITY_EVIDENCE_MISSING")
    gaps["quality"].append("QUALITY_DECISION_UNSIGNED")
    domain_rows = {
        "identity": (identity_ok, inv, True), "inventory": (inventory_ok, inv, True),
        "demand": (bool(sales), captures["sales"], True), "supply": (bool(purchases), captures["purchases"], True),
        "availability": (bool(availability), captures["purchases"], True), "moq": (moq, product, bool(gaps["moq"])),
        "orderMultiple": (multiple, product, True), "quality": (quality_signal, captures["voice"], True),
    }
    sources = {
        "identity": (inv, product, listing, captures["stores"], captures["warehouses"]),
        "inventory": (inv, captures["buckets"]), "demand": (captures["sales"],),
        "supply": (captures["purchases"],),
        "availability": (captures["purchases"], captures["inbound"], product),
        "moq": (product, captures["quotes"]), "orderMultiple": (product,),
        "quality": (product, captures["voice"], captures["inbound"]),
    }
    domains = []
    for name, (observed, capture, partial) in domain_rows.items():
        domains.append(dict(domain=name, state=_state(observed, capture, partial=partial),
                            gaps=sorted(set(gaps[name])), sourceFingerprints=sorted({x.fingerprint for x in captures.values() if x.fingerprint})))
        domains[-1]["sourceFingerprints"] = sorted({x.fingerprint for x in sources[name] if x.fingerprint})
    required_gaps = sorted({gap for values in gaps.values() for gap in values})
    observed_domains = sum(x["state"] in {"OBSERVED", "PARTIAL"} for x in domains)
    newest = max((x.observed_at or "" for x in captures.values()), default="")
    return dict(candidateId=_alias("sku", sku), knownNegativeControl=sku == NEGATIVE_SKU,
                computability="BLOCKED" if required_gaps else "READY_FOR_ADMISSION_REVIEW",
                observedDomains=observed_domains, gapCount=len(required_gaps), newestObservation=newest or None,
                domains=domains, exactGaps=required_gaps)


def build_best_observation(private_path: str | Path, *, tenant_id: str) -> dict[str, Any]:
    """Build a non-calculable D02 observation from one fixed private discovery.

    This performs no network I/O. Source identifiers are converted to stable
    aliases, monetary fields are never projected, and owner confirmation stays
    false because selection authorization is not per-SKU business sign-off.
    """
    path = Path(private_path).resolve()
    if not path.is_relative_to(PRIVATE_ROOT.resolve()) or path.name != "discovery-private.json":
        raise ValueError("CONTROLLED_DISCOVERY_PATH_REJECTED")
    if not isinstance(tenant_id, str) or not 1 <= len(tenant_id) <= 64:
        raise ValueError("TENANT_ID_REJECTED")
    package = json.loads(path.read_text(encoding="utf-8"))
    candidates = package.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("DISCOVERY_CANDIDATES_MISSING")

    parsed = []
    for entry in candidates:
        raw_captures = entry.get("captures") if isinstance(entry, dict) else None
        sku = entry.get("sku") if isinstance(entry, dict) else None
        if not isinstance(sku, str) or not isinstance(raw_captures, dict):
            raise ValueError("DISCOVERY_CANDIDATE_INVALID")
        captures = {}
        for name, raw in raw_captures.items():
            captures[name] = Capture(name, list(raw.get("rows") or []), raw.get("complete"), raw.get("total"),
                                     raw.get("observedAt"), raw.get("fingerprint"), raw.get("error"))
        required = {"inventory", "product", "listing", "stores", "warehouses", "quotes",
                    "buckets", "sales", "purchases", "inbound", "voice"}
        if not required <= captures.keys():
            raise ValueError("DISCOVERY_CAPTURES_INCOMPLETE")
        assessment = assess_candidate(dict(sku=sku, inventory=[], listings=[], products=[]), captures)
        parsed.append((assessment, entry, captures))
    eligible = [x for x in parsed if not x[0]["knownNegativeControl"]] or parsed
    assessment, entry, captures = sorted(
        eligible, key=lambda x: (-x[0]["observedDomains"], x[0]["gapCount"], x[0]["candidateId"]))[0]
    sku = entry["sku"]
    inventory = [x for x in captures["inventory"].rows if x.get("sku") == sku]
    products = [x for x in captures["product"].rows if x.get("sku") == sku]
    listings = [x for x in captures["listing"].rows if x.get("sku") == sku]
    store_ids = sorted({str(x.get("store_id")) for x in inventory if x.get("store_id") is not None})
    warehouse_ids = sorted({str(x.get("wid")) for x in inventory if x.get("wid") is not None})
    if (not inventory or len(products) != 1 or not listings or len(store_ids) != 1 or len(warehouse_ids) != 1
        or captures["inventory"].complete is not True or captures["product"].complete is not True
        or captures["listing"].complete is not True):
        raise ValueError("BEST_CANDIDATE_IDENTITY_INCOMPLETE")
    synthetic_values = {x.get("synthetic") for x in inventory + products if isinstance(x.get("synthetic"), bool)}
    if len(synthetic_values) != 1:
        raise ValueError("SOURCE_SYNTHETIC_UNKNOWN_OR_MIXED")

    def refs(*names: str) -> list[str]:
        return ["read-" + captures[name].fingerprint for name in names if captures[name].fingerprint]

    def times(rows: list[dict[str, Any]], *fields: str) -> list[str]:
        return sorted({str(row[field]) for row in rows for field in fields if row.get(field) is not None})[:20]

    def measure(field: str, value: object, unit: str = "SOURCE_PIECE") -> dict[str, Any]:
        return dict(field=field, value=None if value is None else str(value), unit=unit)

    product = products[0]
    inventory_measurements = [measure(field, row.get(source)) for row in inventory
                              for field, source in (("physical", "quantity"), ("available", "available"))]
    moq_measurements = [measure("moq", product.get("moq"))]
    moq_measurements.extend(measure("quote_moq", row.get("minimum_quantity"))
                            for row in captures["quotes"].rows if row.get("minimum_quantity") is not None)
    identity_complete = all(captures[name].complete is True for name in ("inventory", "product", "listing", "stores", "warehouses"))
    domains = [
        dict(domain="identity", state="OBSERVED" if identity_complete else "INCOMPLETE", measurements=[],
             sourceTimes=times(inventory + products + listings, "updated_at"),
             sourceRefs=refs("inventory", "product", "listing", "stores", "warehouses")),
        dict(domain="inventory", state="INCOMPLETE", measurements=inventory_measurements,
             sourceTimes=times(inventory, "updated_at"), sourceRefs=refs("inventory", "buckets")),
        dict(domain="demand", state="ERROR" if captures["sales"].error else "INCOMPLETE", measurements=[],
             sourceTimes=times(captures["sales"].rows, "order_time", "created_at", "updated_at"), sourceRefs=refs("sales")),
        dict(domain="supply", state="INCOMPLETE", measurements=[],
             sourceTimes=times(captures["purchases"].rows, "order_time", "created_at", "updated_at"), sourceRefs=refs("purchases")),
        dict(domain="availability", state="INCOMPLETE", measurements=[measure("lead_days", product.get("procurement_lead_days"), "DAYS")],
             sourceTimes=times(captures["purchases"].rows + captures["inbound"].rows, "planned_arrival", "updated_at"),
             sourceRefs=refs("product", "purchases", "inbound")),
        dict(domain="moq", state="INCOMPLETE", measurements=moq_measurements,
             sourceTimes=times(products + captures["quotes"].rows, "updated_at", "valid_from", "valid_to"),
             sourceRefs=refs("product", "quotes")),
        dict(domain="orderMultiple", state="INCOMPLETE", measurements=[measure("carton_quantity", product.get("default_carton_qty"))],
             sourceTimes=times(products, "updated_at"), sourceRefs=refs("product")),
        dict(domain="quality", state="INCOMPLETE", measurements=[],
             sourceTimes=times(captures["voice"].rows + captures["inbound"].rows, "business_date", "updated_at", "created_at"),
             sourceRefs=refs("product", "voice", "inbound")),
    ]
    observed_at = max((capture.observed_at for capture in captures.values() if capture.observed_at), default=None)
    if not observed_at:
        raise ValueError("DISCOVERY_OBSERVED_AT_MISSING")
    scope = dict(tenantId=tenant_id, canonicalSkuIds=[_alias("sku", sku)],
                 storeIds=[_alias("store", store_ids[0])], warehouseIds=[_alias("warehouse", warehouse_ids[0])],
                 fields=["quantity"])
    from commerce_hub.data.projection.observed import project_observations
    projection = project_observations(dict(sourceSynthetic=synthetic_values.pop(), ownerConfirmed=False,
        revalidationFailed=any(capture.error is not None for capture in captures.values()), scope=scope,
        observedAt=observed_at, domains=domains))
    return projection.model_dump(mode="json")


def run_discovery(reader: TeachingERPReader, *, candidate_limit: int = MAX_CANDIDATES,
                  verify_count: int = MAX_VERIFIED, now: datetime | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    global_health = check_global_endpoints(reader)
    candidates, discovery = discover_candidates(reader, limit=candidate_limit)
    verified = choose_for_verification(candidates, count=verify_count)
    private_candidates, public_candidates = [], []
    for candidate in verified:
        captures = _capture_candidate(reader, candidate, global_health, now)
        private_candidates.append(dict(sku=candidate["sku"], captures={k: v.private() for k, v in captures.items()}))
        public_candidates.append(assess_candidate(candidate, captures))
    public_candidates.sort(key=lambda x: (x["knownNegativeControl"], -x["observedDomains"], x["gapCount"], x["candidateId"]))
    eligible = [x for x in public_candidates if not x["knownNegativeControl"]]
    best = eligible[0] if eligible else (public_candidates[0] if public_candidates else None)
    tied = [x["candidateId"] for x in eligible if best and
            (x["observedDomains"], x["gapCount"]) == (best["observedDomains"], best["gapCount"])]
    public = dict(schemaVersion="s01-candidate-discovery-v1", generatedAt=now.isoformat(),
                  source="TEACHING_ERP/NETWORK_READ/OBSERVED_FACT", candidateLimit=candidate_limit,
                  discoveredCount=len(candidates), verifiedCount=len(public_candidates),
                  globalEndpoints={k: dict(state="ERROR" if v.error else "REACHABLE", error=v.error,
                                                   complete=v.complete, total=v.total, fingerprint=v.fingerprint)
                                   for k, v in global_health.items()},
                  candidates=public_candidates,
                  recommendation=dict(candidateId=best["candidateId"] if best else None,
                                      tiedCandidateIds=tied,
                                      status="CLOSEST_TIED_BLOCKED_SAMPLE" if len(tied) > 1 else "CLOSEST_BLOCKED_SAMPLE" if best else "NO_CANDIDATE",
                                      exactGaps=best["exactGaps"] if best else ["NO_CANDIDATE"]),
                  interpretation="Empty source results are UNKNOWN and never converted to zero.",
                  realBusinessAdmission="BLOCKED")
    private = dict(schemaVersion="s01-candidate-discovery-private-v1", generatedAt=now.isoformat(),
                   globalEndpoints={k: v.private() for k, v in global_health.items()},
                   discovery={k: v.private() for k, v in discovery.items()}, candidates=private_candidates,
                   readerEvents=reader.events)
    return public, private


def _reader_with_private_transport(run_dir: Path) -> TeachingERPReader:
    values = dotenv_values(ROOT / ".env.erp", interpolate=False)
    config = ERPConfig(base_url=values.get("ERP_BASE_URL") or "https://47.107.76.124/lingxing-erp",
                       username=values.get("ERP_USERNAME") or "", password=values.get("ERP_PASSWORD") or "",
                       access_token=values.get("ERP_ACCESS_TOKEN") or "", timeout=15, max_requests=100)
    serial = [0]
    def transport(method: str, path: str, headers: dict[str, str], body: bytes | None, settings: ERPConfig):
        status, raw = https_transport(method, path, headers, body, settings)
        if not path.startswith(AUTH_PATH):
            serial[0] += 1
            (run_dir / f"response-{serial[0]:03d}.json").write_bytes(raw)
        return status, raw
    return TeachingERPReader(config, transport=transport)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-limit", type=int, default=MAX_CANDIDATES)
    parser.add_argument("--verify-count", type=int, default=MAX_VERIFIED)
    parser.add_argument("--build-observation-from", type=Path)
    parser.add_argument("--tenant-id")
    args = parser.parse_args()
    if args.build_observation_from:
        try:
            projection = build_best_observation(args.build_observation_from, tenant_id=args.tenant_id or "")
            target = args.build_observation_from.resolve().parent / "best-observation.json"
            target.write_bytes(_json_bytes(projection))
            print(json.dumps(dict(result="PASS", projectionRef=target.relative_to(ROOT).as_posix(),
                                  revision=projection["revision"], scope=projection["scope"],
                                  ownerConfirmed=projection["ownerConfirmed"],
                                  realBusinessAdmission="BLOCKED")))
            return 0
        except Exception as error:
            print(json.dumps(dict(result="FAIL", code=error.code if isinstance(error, ERPError) else str(error))))
            return 1
    run_dir = PRIVATE_ROOT / (datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ-") + uuid4().hex[:8])
    run_dir.mkdir(parents=True, exist_ok=False)
    try:
        reader = _reader_with_private_transport(run_dir)
        public, private = run_discovery(reader, candidate_limit=args.candidate_limit, verify_count=args.verify_count)
        (run_dir / "discovery-private.json").write_bytes(_json_bytes(private))
        PUBLIC_ROOT.mkdir(parents=True, exist_ok=True)
        (PUBLIC_ROOT / "candidate-matrix.json").write_bytes(_json_bytes(public))
        private_ref = run_dir.relative_to(ROOT).as_posix()
        (PUBLIC_ROOT / "README.md").write_text(
            "# S01 教学 ERP 候选发现报告\n\n"
            f"生成时间：{public['generatedAt']}。先检查全局销量与采购接口，再在最多20个候选中核验3—5个。\n\n"
            f"推荐状态：`{public['recommendation']['status']}`；真实业务准入：`{public['realBusinessAdmission']}`。"
            "空返回保持UNKNOWN，不解释为零。SKT-OL-XXL保留为已知数据不足负例。\n\n"
            f"私有包：`{private_ref}`（不提交）。\n", encoding="utf-8")
        print(json.dumps(dict(result="PASS", verified=public["verifiedCount"],
                              recommendation=public["recommendation"]["candidateId"],
                              admission=public["realBusinessAdmission"], privateRef=private_ref)))
        return 0
    except Exception as error:
        print(json.dumps(dict(result="FAIL", code=error.code if isinstance(error, ERPError) else type(error).__name__)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
