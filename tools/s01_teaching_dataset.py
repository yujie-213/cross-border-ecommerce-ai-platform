"""Create and verify one isolated S01 teaching dataset through documented ERP CRUD.

The tool is deliberately separate from the production/read-only connector.  Every
mutation is journaled before it is sent, raw request/response material stays below
``data/private``, and a successful POST is accepted only after an independent GET.
No workflow, payment, shipment, approval, stock-posting, or notification endpoint
is callable from this module.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import hashlib
import http.client
import json
from pathlib import Path
import ssl
import time
from typing import Any
from urllib.parse import urlencode
import re

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
BASE_HOST = "47.107.76.124"
BASE_PATH = "/lingxing-erp"
BASE_URL = f"https://{BASE_HOST}{BASE_PATH}"
AUTH_PATH = "/api/auth-server/oauth/access-token"
OPENAPI_VERSION = "5.1.0"
OPENAPI_RELEASE = "20260917-teaching-final-v2"
BATCH_ID = "S01-AI-TEST-20261112"
SOURCE_NATURE = "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"
PRIVATE_ROOT = ROOT / "data/private/s01-teaching-dataset"
PUBLIC_ROOT = ROOT / "docs/evidence/S01-BACKEND/teaching-data"
AUTHORIZATION_ID = "s01-backend-20261112-v1"

RESOURCES = {
    "product": ("products", "create_products", "update_products", "get_products", "sku"),
    "listing": ("listings", "create_listings", "update_listings", "get_listings", "listing_id"),
    "inventory": ("inventory", "create_inventory", "update_inventory", "get_inventory", "batch_no"),
    "sales": ("sales-orders", "create_sales_orders", "update_sales_orders", "get_sales_orders", "order_sn"),
    "purchase": ("purchase-orders", "create_purchase_orders", "update_purchase_orders", "get_purchase_orders", "order_sn"),
    "quality": ("inbound-orders", "create_inbound_orders", "update_inbound_orders", "get_inbound_orders", "order_sn"),
}
SERVER_FIELDS = {"id", "tenant_id", "created_at", "updated_at", "economics"}


class DatasetError(RuntimeError):
    def __init__(self, code: str, status: int | None = None):
        self.code, self.status = code, status
        super().__init__(code)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      default=str).encode("utf-8")


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def alias(kind: str, value: object) -> str:
    return f"{kind}-{hashlib.sha256(str(value).encode()).hexdigest()[:20]}"


def business_content(record: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Extract only fields the documented write contract accepted."""
    return {key: record.get(key) for key in sorted(request) if key not in SERVER_FIELDS}


@dataclass(frozen=True)
class Config:
    username: str = field(repr=False)
    password: str = field(repr=False)
    access_token: str = field(default="", repr=False)
    timeout: float = 15


class Journal:
    def __init__(self, path: Path):
        self.path = path
        self.value: dict[str, Any] = {
            "schemaVersion": "s01-teaching-dataset-journal-v1",
            "batchId": BATCH_ID,
            "sourceNature": SOURCE_NATURE,
            "openapi": {"version": OPENAPI_VERSION, "release": OPENAPI_RELEASE},
            "records": [],
        }
        if path.exists():
            self.value = json.loads(path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(self.value) + b"\n")
        temporary.replace(self.path)

    def append(self, value: dict[str, Any]) -> int:
        self.value["records"].append(value)
        self.save()
        return len(self.value["records"]) - 1

    def update(self, index: int, **values: Any) -> None:
        self.value["records"][index].update(values)
        self.save()

    def verified(self, resource: str, business_key: str) -> dict[str, Any] | None:
        matches = [x for x in self.value["records"] if x.get("resource") == resource
                   and x.get("businessKey") == business_key and x.get("state") == "VERIFIED"]
        return matches[-1] if matches else None

    def unresolved(self, resource: str, business_key: str) -> dict[str, Any] | None:
        unresolved_states = {"SENDING", "SENT", "UPDATE_SENDING", "UPDATED", "UNKNOWN"}
        matches = [x for x in self.value["records"] if x.get("resource") == resource
                   and x.get("businessKey") == business_key and x.get("state") in unresolved_states]
        return matches[-1] if matches else None


class TeachingDatasetClient:
    def __init__(self, config: Config, raw_dir: Path, *, sleeper=time.sleep):
        self.config, self.raw_dir, self.sleeper = config, raw_dir, sleeper
        self.token = config.access_token
        self.owned_mutations: set[tuple[str, str]] = set()
        raw_dir.mkdir(parents=True, exist_ok=True)
        serials = []
        for path in raw_dir.glob("response-*.json"):
            match = re.fullmatch(r"response-(\d+)\.json", path.name)
            if match:
                serials.append(int(match.group(1)))
        self.serial = max(serials, default=0)

    def authorize_owned(self, resource: str, record_id: object) -> None:
        if resource not in {value[0] for value in RESOURCES.values()} or record_id is None:
            raise DatasetError("ERP_OWNED_RECORD_REJECTED")
        self.owned_mutations.add((resource, str(record_id)))

    def _allow(self, method: str, path: str, *, auth: bool) -> None:
        resources = {value[0] for value in RESOURCES.values()}
        if auth:
            if method == "POST" and path == AUTH_PATH:
                return
            raise DatasetError("ERP_OPERATION_NOT_ALLOWLISTED")
        if "://" in path or "?" in path or ".." in path or not path.startswith("/api/v1/"):
            raise DatasetError("ERP_OPERATION_NOT_ALLOWLISTED")
        collection = re.fullmatch(r"/api/v1/([a-z-]+)", path)
        detail = re.fullmatch(r"/api/v1/([a-z-]+)/([^/]+)", path)
        if method == "GET" and ((collection and collection.group(1) in resources)
            or (detail and detail.group(1) in resources)):
            return
        if method == "POST" and collection and collection.group(1) in resources:
            return
        if method in {"PUT", "DELETE"} and detail:
            resource, record_id = detail.groups()
            if ((resource, record_id) in self.owned_mutations
                and not (method == "DELETE" and resource == "sales-orders")):
                return
        raise DatasetError("ERP_OPERATION_NOT_ALLOWLISTED")

    def _transport(self, method: str, path: str, headers: dict[str, str], body: bytes | None) -> tuple[int, bytes]:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        connection = http.client.HTTPSConnection(BASE_HOST, timeout=self.config.timeout, context=context)
        try:
            connection.request(method, BASE_PATH + path, body=body, headers=headers)
            response = connection.getresponse()
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise DatasetError("ERP_RESPONSE_LIMIT")
            return response.status, raw
        finally:
            connection.close()

    def authenticate(self) -> None:
        if self.token:
            return
        if not self.config.username or not self.config.password:
            raise DatasetError("ERP_CREDENTIALS_MISSING")
        result, _, _, _ = self.request("POST", AUTH_PATH,
            {"appId": self.config.username, "appSecret": self.config.password}, auth=True)
        data = result.get("data") if isinstance(result, dict) else None
        token = data.get("access_token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not token or "\r" in token or "\n" in token:
            raise DatasetError("ERP_AUTH_ENVELOPE_REJECTED")
        self.token = token

    def request(self, method: str, path: str, values: dict[str, Any] | None = None, *,
                auth: bool = False) -> tuple[dict[str, Any], str, str, str]:
        self._allow(method, path, auth=auth)
        if not auth:
            self.authenticate()
        values = dict(values or {})
        headers = {"Accept": "application/json"}
        if not auth:
            headers["Authorization"] = "Bearer " + self.token
        body = None
        target = path
        if method in {"POST", "PUT"}:
            body = canonical_bytes(values)
            headers["Content-Type"] = "application/json"
        elif values:
            target += "?" + urlencode(values, doseq=True)
        observed_at = datetime.now(timezone.utc).isoformat()
        try:
            status, raw = self._transport(method, target, headers, body)
        except DatasetError:
            raise
        except TimeoutError:
            raise DatasetError("ERP_TIMEOUT") from None
        except Exception:
            raise DatasetError("ERP_TRANSPORT_FAILURE") from None
        raw_sha = hashlib.sha256(raw).hexdigest()
        self.serial += 1
        ref = self.raw_dir / f"response-{self.serial:03d}.json"
        ref.write_bytes(raw)
        if 300 <= status < 400:
            raise DatasetError("ERP_REDIRECT_REJECTED", status)
        expected = {"GET": {200}, "POST": {200, 201}, "PUT": {200}, "DELETE": {200}}[method]
        if status not in expected:
            raise DatasetError("ERP_SCOPE_DENIED" if status == 403 else "ERP_HTTP_ERROR", status)
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise DatasetError("ERP_INVALID_JSON") from None
        if not isinstance(result, dict):
            raise DatasetError("ERP_INVALID_ENVELOPE")
        return result, raw_sha, observed_at, ref.relative_to(ROOT).as_posix()

    def exact(self, resource: str, field: str, value: str) -> list[dict[str, Any]]:
        result, _, _, _ = self.request("GET", f"/api/v1/{resource}",
            {"field": field, "q": value, "match": "exact", "offset": 0, "limit": 20,
             **({"view": "full"} if resource in {"inventory", "sales-orders"} else {})})
        rows = result.get("items")
        total = result.get("total")
        if (not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows)
                or not isinstance(total, int) or isinstance(total, bool) or total < 0):
            raise DatasetError("ERP_INVALID_PAGE")
        if total != len(rows) or total > 20:
            raise DatasetError("ERP_PAGINATION_INCOMPLETE")
        return rows


def operation_ref(operation_id: str, resource: str, record_id: object | None = None) -> str:
    suffix = f"/{alias('record', record_id)}" if record_id is not None else ""
    return f"openapi:{OPENAPI_VERSION}/{OPENAPI_RELEASE}/{operation_id}/{resource}{suffix}"


def scope_digest(seed: dict[str, Any]) -> str:
    return digest({key: seed[key] for key in ("store_id", "store_name", "wid", "warehouse_name")})


def discover_scope(client: TeachingDatasetClient) -> dict[str, Any]:
    result, _, _, _ = client.request("GET", "/api/v1/inventory",
        {"offset": 0, "limit": 20, "view": "full"})
    rows = result.get("items")
    if not isinstance(rows, list):
        raise DatasetError("ERP_SCOPE_DISCOVERY_INVALID")
    for row in rows:
        if isinstance(row, dict) and all(row.get(k) is not None for k in
            ("store_id", "store_name", "wid", "warehouse_name")):
            return {k: row[k] for k in ("store_id", "store_name", "wid", "warehouse_name")}
    raise DatasetError("ERP_AUTHORIZED_STORE_WAREHOUSE_NOT_FOUND")


def dataset_requests(seed: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    sku = BATCH_ID + "-A"
    product = dict(sku=sku, name="S01 teaching replenishment sample A", model="TEACHING-A",
        category="TEACHING_TEST", status="ACTIVE", price=10, cost=4, product_type="TEACHING_SIMULATION",
        identifier=BATCH_ID + "-A", unit="piece", material="teaching-only", brand="TEACHING",
        tag=BATCH_ID, developer="CommerceHub", owner="Teaching", description=SOURCE_NATURE,
        supplier_name="TEACHING-SUPPLIER", moq=12, procurement_lead_days=7,
        default_carton_qty=6, qc_method="AQL", qc_standard="AQL-2.5")
    listing = dict(sku=sku, platform="Amazon", store_name=seed["store_name"],
        listing_id=BATCH_ID + "-LISTING-A", title="S01 teaching listing A", price=10, stock=96)
    # One owned inventory row is updated sequentially for A-E. Each state is GET-captured
    # before the next update, so a case never selects one row from a multi-batch total.
    requests: list[tuple[str, str, dict[str, Any]]] = [("product", sku, product),
        ("listing", listing["listing_id"], listing)]
    inventory = dict(batch_no=BATCH_ID + "-INV-A", wid=seed["wid"], warehouse_name=seed["warehouse_name"],
        sku=sku, fnsku=BATCH_ID + "-FNSKU-A", store_id=seed["store_id"], store_name=seed["store_name"],
        quantity=60, available=60, source_batch_no=BATCH_ID + "-A", order_sn=BATCH_ID + "-INV-A")
    requests.append(("inventory", inventory["batch_no"], inventory))
    quantities = [8, 10, 9, 11, 12, 14, 13]
    first_day = date(2026, 11, 1)
    for index in range(7):
        day = first_day + timedelta(days=index)
        order = BATCH_ID + f"-SALE-{day:%Y%m%d}"
        items = [dict(sku=sku, quantity=quantities[index], unit_price=10,
                      amount=quantities[index] * 10)]
        requests.append(("sales", order, dict(order_sn=order, platform_order_sn=order,
            platform="Amazon", store_name=seed["store_name"], site="US", country="US",
            order_time=f"{day.isoformat()} 12:00:00", currency="USD",
            amount=sum(item["amount"] for item in items),
            shipping_warehouse=seed["warehouse_name"], delivery_method="TEACHING_ONLY",
            remark=BATCH_ID, item_list=items)))
    quality_order = BATCH_ID + "-QC-A"
    requests.append(("quality", quality_order, dict(order_sn=quality_order, type=1,
        warehouse_name=seed["warehouse_name"],
        supplier_name="TEACHING-SUPPLIER", create_time="2026-11-09 09:00:00", quantity=120,
        purchase_unit_price=4, freight=0, other_fee=0, allocation_method="TEACHING_ONLY",
        inspected_qty=20, available_qty=20, defective_qty=0, qc_status="TEACHING_QUALITY_CLEAR",
        remark=BATCH_ID, item_list=[dict(sku=sku, quantity=120, inspected_qty=20,
                                         available_qty=20, defective_qty=0)])))
    return requests


def purchase_c_request(seed: dict[str, Any]) -> dict[str, Any]:
    order = BATCH_ID + "-PURCHASE-C"
    return dict(order_sn=order, custom_order_sn=order, supplier_name="TEACHING-SUPPLIER",
        warehouse_name=seed["warehouse_name"], order_time="2026-11-12 09:00:00",
        purchase_currency="USD", amount=268, purchase_user="CommerceHub-Teaching",
        planned_arrival="2026-11-19", tax_rate=0, freight=0, other_fee=0,
        allocation_method="TEACHING_ONLY", qc_type="TEACHING_DRAFT",
        payment_plan="NOT_SUBMITTED", source_plan_no=BATCH_ID + "-PLAN-C", remark=BATCH_ID,
        item_list=[dict(sku=BATCH_ID + "-A", quantity=67, unit_price=4, amount=268)])


def verify_or_create(client: TeachingDatasetClient, journal: Journal, resource_name: str,
                     business_key: str, request: dict[str, Any], seed_scope_digest: str) -> dict[str, Any]:
    resource, create_op, update_op, get_op, key_field = RESOURCES[resource_name]
    existing = journal.verified(resource_name, business_key)
    request_sha = digest(request)
    # An empty exact query cannot prove a timed-out or interrupted mutation was not applied.
    # Preserve the original attempt for operator inspection and never blind-resend it.
    unresolved = journal.unresolved(resource_name, business_key)
    if unresolved:
        previous = existing
        record_id = previous.get("recordId") if previous else None
        if record_id is None:
            raise DatasetError("ERP_PREVIOUS_SEND_UNRESOLVED")
        read, raw_sha, observed_at, artifact_ref = client.request("GET", f"/api/v1/{resource}/{record_id}")
        content = business_content(read, request)
        if content != business_content(request, request):
            raise DatasetError("ERP_PREVIOUS_SEND_UNRESOLVED")
        if unresolved.get("requestDigest") == request_sha:
            journal.update(journal.value["records"].index(unresolved), state="VERIFIED", recordId=record_id,
                recordAlias=alias("record", record_id), writeReceiptRef="trusted-artifact:unknown-send-journal",
                writeReceiptSHA256=request_sha, writeArtifactDigest=request_sha, readBackBatchId=BATCH_ID,
                readBackOperationRef=operation_ref(get_op, resource, record_id), readBackArtifactRef=artifact_ref,
                readBackRawResponseSHA256=raw_sha, readBackObservedAt=observed_at,
                readScopeDigest=seed_scope_digest, readBackContentDigest=digest(content),
                resolution="APPLIED_CONFIRMED_BY_GET")
            return unresolved
        journal.update(journal.value["records"].index(unresolved), state="NOT_APPLIED_CONFIRMED",
                       resolution="CURRENT_GET_MATCHES_PREVIOUS_VERIFIED_RECORD",
                       readBackRawResponseSHA256=raw_sha, readBackObservedAt=observed_at)
        if previous and previous.get("requestDigest") == request_sha:
            return previous
        raise DatasetError("ERP_PREVIOUS_SEND_UNRESOLVED")
    if existing and existing.get("requestDigest") == request_sha:
        return existing
    if existing:
        record_id = existing.get("recordId")
        if record_id is None:
            raise DatasetError("ERP_RECORD_ID_UNRESOLVED")
        index = journal.append(dict(resource=resource_name, businessKey=business_key,
            businessKeyAlias=alias(resource_name, business_key), state="UPDATE_SENDING",
            requestDigest=request_sha, writeScopeDigest=seed_scope_digest,
            writeOperationRef=operation_ref(update_op, resource, record_id),
            writeBatchId=BATCH_ID, sourceNature=SOURCE_NATURE, supersedes=existing.get("recordAlias")))
        try:
            client.authorize_owned(resource, record_id)
            receipt, receipt_sha, receipt_at, receipt_ref = client.request(
                "PUT", f"/api/v1/{resource}/{record_id}", request)
            journal.update(index, state="UPDATED", writeReceiptRef=receipt_ref,
                writeReceiptSHA256=receipt_sha, writeObservedAt=receipt_at)
        except DatasetError as error:
            journal.update(index, state="UNKNOWN" if error.code in {"ERP_TRANSPORT_FAILURE", "ERP_TIMEOUT"} else "FAILED",
                           error=error.code, httpStatus=error.status)
            raise
        read, raw_sha, observed_at, artifact_ref = client.request("GET", f"/api/v1/{resource}/{record_id}")
        content = business_content(read, request)
        if content != business_content(request, request):
            journal.update(index, state="FAILED", error="ERP_READBACK_CONTENT_MISMATCH")
            raise DatasetError("ERP_READBACK_CONTENT_MISMATCH")
        journal.update(index, state="VERIFIED", recordId=record_id, recordAlias=alias("record", record_id),
            writeArtifactDigest=request_sha, readBackBatchId=BATCH_ID,
            readBackOperationRef=operation_ref(get_op, resource, record_id), readBackArtifactRef=artifact_ref,
            readBackRawResponseSHA256=raw_sha, readBackObservedAt=observed_at,
            readScopeDigest=seed_scope_digest, readBackContentDigest=digest(content))
        return journal.value["records"][index]
    matches = client.exact(resource, key_field, business_key)
    if len(matches) > 1:
        raise DatasetError("ERP_BUSINESS_KEY_NOT_UNIQUE")
    entry = dict(resource=resource_name, businessKey=business_key, businessKeyAlias=alias(resource_name, business_key),
        state="SENDING", requestDigest=request_sha, writeScopeDigest=seed_scope_digest,
        writeOperationRef=operation_ref(create_op, resource), writeBatchId=BATCH_ID,
        sourceNature=SOURCE_NATURE)
    index = journal.append(entry)
    try:
        if matches:
            receipt, receipt_sha, receipt_at, receipt_ref = matches[0], None, None, None
            journal.update(index, state="FOUND_BEFORE_SEND")
        else:
            receipt, receipt_sha, receipt_at, receipt_ref = client.request("POST", f"/api/v1/{resource}", request)
            journal.update(index, state="SENT", writeReceiptRef=receipt_ref,
                writeReceiptSHA256=receipt_sha, writeObservedAt=receipt_at)
    except DatasetError as error:
        journal.update(index, state="UNKNOWN" if error.code in {"ERP_TRANSPORT_FAILURE", "ERP_TIMEOUT"} else "FAILED",
                       error=error.code, httpStatus=error.status)
        raise
    record_id = receipt.get("id")
    if record_id is None:
        matches = client.exact(resource, key_field, business_key)
        if len(matches) != 1 or matches[0].get("id") is None:
            journal.update(index, state="UNKNOWN", error="ERP_RECORD_ID_UNRESOLVED")
            raise DatasetError("ERP_RECORD_ID_UNRESOLVED")
        record_id = matches[0]["id"]
    read, raw_sha, observed_at, artifact_ref = client.request("GET", f"/api/v1/{resource}/{record_id}")
    content = business_content(read, request)
    if content != business_content(request, request):
        journal.update(index, state="FAILED", error="ERP_READBACK_CONTENT_MISMATCH")
        raise DatasetError("ERP_READBACK_CONTENT_MISMATCH")
    artifact_digest = digest(content)
    journal.update(index, state="VERIFIED", recordId=record_id, recordAlias=alias("record", record_id),
        writeArtifactDigest=request_sha, readBackBatchId=BATCH_ID,
        readBackOperationRef=operation_ref(get_op, resource, record_id),
        readBackArtifactRef=artifact_ref, readBackRawResponseSHA256=raw_sha,
        readBackObservedAt=observed_at, readScopeDigest=seed_scope_digest,
        readBackContentDigest=artifact_digest)
    return journal.value["records"][index]


def verify_empty_purchase_collection(client: TeachingDatasetClient, journal: Journal,
                                     seed_scope_digest: str, *, refresh: bool = False) -> dict[str, Any]:
    """Bind A's zero supply to one formal, exact, batch-matched ERP list GET."""

    business_key = BATCH_ID + "-PURCHASE-A-EMPTY"
    existing = journal.verified("purchase-empty", business_key)
    if existing and not refresh:
        return existing
    query = {"order_sn": BATCH_ID + "-PURCHASE-A", "match": "exact", "offset": 0, "limit": 20}
    result, raw_sha, observed_at, artifact_ref = client.request(
        "GET", "/api/v1/purchase-orders", query
    )
    rows = result.get("items")
    total = result.get("total")
    if not isinstance(rows, list) or rows or total != 0:
        raise DatasetError("ERP_PURCHASE_EMPTY_SET_NOT_PROVEN")
    entry = dict(
        resource="purchase-empty", businessKey=business_key,
        businessKeyAlias=alias("purchase-empty", business_key), state="VERIFIED",
        requestDigest=digest(query), writeBatchId=BATCH_ID, readBackBatchId=BATCH_ID,
        sourceNature=SOURCE_NATURE, writeScopeDigest=seed_scope_digest,
        readScopeDigest=seed_scope_digest,
        readBackOperationRef=operation_ref("list_purchase_orders", "purchase-orders"),
        readBackArtifactRef=artifact_ref, readBackRawResponseSHA256=raw_sha,
        readBackObservedAt=observed_at,
        readBackContentDigest=digest({"items": [], "total": 0}), recordIds=[], recordCount=0,
        completeness="EXACT_BATCH_MATCH_COMPLETE",
    )
    if existing:
        journal.update(journal.value["records"].index(existing), **entry)
        return existing
    journal.append(entry)
    return entry


def verify_scope_collections(client: TeachingDatasetClient, journal: Journal,
                             seed_scope_digest: str, *, refresh: bool = False) -> None:
    checks = [("inventory-collection", "/api/v1/inventory",
        {"field": "batch_no", "q": BATCH_ID + "-INV-A", "match": "exact",
         "offset": 0, "limit": 20, "view": "full"}, 1)]
    for resource, path, query, expected in checks:
        existing = journal.verified(resource, BATCH_ID)
        if existing and not refresh:
            continue
        result, raw_sha, observed_at, artifact_ref = client.request("GET", path, query)
        rows, total = result.get("items"), result.get("total")
        if (not isinstance(rows, list) or not isinstance(total, int) or isinstance(total, bool)
                or total != len(rows) or total != expected or total > 20
                or any(not isinstance(row, dict) or row.get("id") is None for row in rows)):
            raise DatasetError("ERP_COLLECTION_SCOPE_INCOMPLETE")
        record_ids = [str(row["id"]) for row in rows]
        if len(set(record_ids)) != expected:
            raise DatasetError("ERP_COLLECTION_SCOPE_DUPLICATE")
        entry = dict(resource=resource, businessKey=BATCH_ID,
            businessKeyAlias=alias(resource, BATCH_ID), state="VERIFIED",
            requestDigest=digest(query), writeBatchId=BATCH_ID, readBackBatchId=BATCH_ID,
            sourceNature=SOURCE_NATURE, writeScopeDigest=seed_scope_digest,
            readScopeDigest=seed_scope_digest,
            readBackOperationRef=operation_ref(
                "list_inventory" if resource == "inventory-collection" else "list_sales_orders",
                "inventory" if resource == "inventory-collection" else "sales-orders"),
            readBackArtifactRef=artifact_ref, readBackRawResponseSHA256=raw_sha,
            readBackObservedAt=observed_at, readBackContentDigest=digest({"recordIds": sorted(record_ids)}),
            recordIds=record_ids, recordCount=expected, completeness="EXACT_SCOPE_COMPLETE")
        if existing:
            journal.update(journal.value["records"].index(existing), **entry)
        else:
            journal.append(entry)
    existing = journal.verified("sales-collection", BATCH_ID)
    if existing and not refresh:
        return
    rows, raw_digests, artifact_refs, observed = [], [], [], []
    for day in range(1, 8):
        order = BATCH_ID + f"-SALE-202611{day:02d}"
        query = {"field": "order_sn", "q": order, "match": "exact",
                 "offset": 0, "limit": 20, "view": "full"}
        result, raw_sha, observed_at, artifact_ref = client.request(
            "GET", "/api/v1/sales-orders", query)
        items, total = result.get("items"), result.get("total")
        if (not isinstance(items, list) or total != 1 or len(items) != 1
                or not isinstance(items[0], dict) or items[0].get("order_sn") != order
                or not items[0].get("item_list")
                or items[0]["item_list"][0].get("sku") != BATCH_ID + "-A"):
            raise DatasetError("ERP_COLLECTION_SCOPE_INCOMPLETE")
        rows.extend(items); raw_digests.append(raw_sha); artifact_refs.append(artifact_ref)
        observed.append(observed_at)
    record_ids = [str(row.get("id")) for row in rows]
    if any(value == "None" for value in record_ids) or len(set(record_ids)) != 7:
        raise DatasetError("ERP_COLLECTION_SCOPE_DUPLICATE")
    entry = dict(resource="sales-collection", businessKey=BATCH_ID,
        businessKeyAlias=alias("sales-collection", BATCH_ID), state="VERIFIED",
        requestDigest=digest([BATCH_ID + f"-SALE-202611{day:02d}" for day in range(1, 8)]),
        writeBatchId=BATCH_ID, readBackBatchId=BATCH_ID, sourceNature=SOURCE_NATURE,
        writeScopeDigest=seed_scope_digest, readScopeDigest=seed_scope_digest,
        readBackOperationRef=operation_ref("list_sales_orders", "sales-orders"),
        readBackArtifactRef="private-artifact:sales-seven-exact-list-gets",
        privateReadBackArtifactRefs=artifact_refs,
        readBackRawResponseSHA256=digest(sorted(raw_digests)),
        readBackObservedAt=max(observed), readBackContentDigest=digest({"recordIds": sorted(record_ids)}),
        recordIds=record_ids, recordCount=7, completeness="SEVEN_EXACT_KEYS_COMPLETE_NO_MIRRORS")
    if existing:
        journal.update(journal.value["records"].index(existing), **entry)
    else:
        journal.append(entry)


def refresh_verified_readbacks(client: TeachingDatasetClient, journal: Journal,
                               requests: list[tuple[str, str, dict[str, Any]]],
                               seed_scope_digest: str) -> None:
    """Re-capture immutable raw GET evidence without sending any mutation."""

    for resource_name, business_key, request in requests:
        row = journal.verified(resource_name, business_key)
        if row is None or row.get("recordId") is None:
            raise DatasetError("ERP_VERIFIED_RECORD_MISSING")
        resource, _, _, get_op, _ = RESOURCES[resource_name]
        record_id = row["recordId"]
        read, raw_sha, observed_at, artifact_ref = client.request(
            "GET", f"/api/v1/{resource}/{record_id}"
        )
        content = business_content(read, request)
        if content != business_content(request, request):
            raise DatasetError("ERP_READBACK_CONTENT_MISMATCH")
        journal.update(
            journal.value["records"].index(row),
            readBackBatchId=BATCH_ID,
            readBackOperationRef=operation_ref(get_op, resource, record_id),
            readBackArtifactRef=artifact_ref,
            readBackRawResponseSHA256=raw_sha,
            readBackObservedAt=observed_at,
            readScopeDigest=seed_scope_digest,
            readBackContentDigest=digest(content),
        )


def capture_inventory_case(client: TeachingDatasetClient, journal: Journal,
                           request: dict[str, Any], seed_scope_digest: str,
                           case_id: str) -> dict[str, Any]:
    """Freeze one sequential state of the single owned inventory row via PUT then GET."""

    business_key = request["batch_no"]
    request_sha = digest(request)
    matches = [row for row in journal.value["records"] if row.get("resource") == "inventory"
               and row.get("businessKey") == business_key and row.get("caseId") == case_id
               and row.get("state") == "VERIFIED" and row.get("requestDigest") == request_sha]
    if matches:
        return matches[-1]
    existing = journal.verified("inventory", business_key)
    if existing is None or existing.get("recordId") is None:
        raise DatasetError("ERP_VERIFIED_RECORD_MISSING")
    record_id = existing["recordId"]
    index = journal.append(dict(resource="inventory", businessKey=business_key,
        businessKeyAlias=alias("inventory", business_key), caseId=case_id, state="UPDATE_SENDING",
        requestDigest=request_sha, writeScopeDigest=seed_scope_digest,
        writeOperationRef=operation_ref("update_inventory", "inventory", record_id),
        writeBatchId=BATCH_ID, sourceNature=SOURCE_NATURE, supersedes=existing.get("recordAlias")))
    try:
        client.authorize_owned("inventory", record_id)
        receipt, receipt_sha, receipt_at, receipt_ref = client.request(
            "PUT", f"/api/v1/inventory/{record_id}", request
        )
        journal.update(index, state="UPDATED", writeReceiptRef=receipt_ref,
                       writeReceiptSHA256=receipt_sha, writeObservedAt=receipt_at)
    except DatasetError as error:
        journal.update(index, state="UNKNOWN" if error.code in {"ERP_TRANSPORT_FAILURE", "ERP_TIMEOUT"}
                       else "FAILED", error=error.code, httpStatus=error.status)
        raise
    read, raw_sha, observed_at, artifact_ref = client.request("GET", f"/api/v1/inventory/{record_id}")
    if business_content(receipt, request) != business_content(request, request):
        raise DatasetError("ERP_WRITE_RECEIPT_CONTENT_MISMATCH")
    if business_content(read, request) != business_content(request, request):
        raise DatasetError("ERP_READBACK_CONTENT_MISMATCH")
    if receipt.get("updated_at") is None or receipt.get("updated_at") != read.get("updated_at"):
        raise DatasetError("ERP_WRITE_READ_TIMESTAMP_MISMATCH")
    journal.update(index, state="VERIFIED", recordId=record_id,
        recordAlias=alias("record", record_id), writeArtifactDigest=request_sha,
        readBackBatchId=BATCH_ID, readBackOperationRef=operation_ref("get_inventory", "inventory", record_id),
        readBackArtifactRef=artifact_ref, readBackRawResponseSHA256=raw_sha,
        readBackObservedAt=observed_at, readScopeDigest=seed_scope_digest,
        readBackContentDigest=digest(business_content(read, request)))
    return journal.value["records"][index]


def public_evidence(journal: Journal, scope_sha: str) -> dict[str, Any]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for row in journal.value["records"]:
        if row.get("resource") == "purchase":
            continue
        if row.get("resource") == "inventory" and row.get("caseId") not in {None, "A"}:
            continue
        if row.get("resource") and row.get("businessKey"):
            latest[(row["resource"], row["businessKey"])] = row
    verified = [row for row in latest.values() if row.get("state") == "VERIFIED"]
    resources = []
    for row in verified:
        resource = {key: row.get(key) for key in (
            "resource", "businessKeyAlias", "state", "writeOperationRef", "readBackOperationRef",
            "writeReceiptSHA256", "writeArtifactDigest", "readBackRawResponseSHA256",
            "readBackObservedAt", "readBackContentDigest", "writeScopeDigest", "readScopeDigest",
            "recordAlias", "recordCount", "completeness")}
        for key in ("writeOperationRef", "readBackOperationRef"):
            if isinstance(resource.get(key), str) and resource[key].startswith("openapi-"):
                resource[key] = "openapi:" + resource[key][len("openapi-"):]
        resources.append(resource)
    counts: dict[str, int] = {}
    for row in resources:
        counts[row["resource"]] = counts.get(row["resource"], 0) + 1
    value = dict(schemaVersion="s01-teaching-dataset-evidence-v1", batchId=BATCH_ID,
        writeBatchId=BATCH_ID, readBackBatchId=BATCH_ID, sourceNature=SOURCE_NATURE,
        openapi=dict(version=OPENAPI_VERSION, release=OPENAPI_RELEASE), scopeDigest=scope_sha,
        result="PASS" if (len(resources) == 14 and counts.get("purchase-empty") == 1
                          and counts.get("inventory-collection") == 1
                          and counts.get("sales-collection") == 1) else "PARTIAL",
        resourceCounts=counts,
        records=resources, safety=dict(externalPlatformOperations=False, payment=False, shipment=False,
            purchaseSubmission=False, approval=False, stockPosting=False, notifications=False,
            salesDeletionSupported=False),
        interpretation=("Each write is verified by a separate GET; A supply is additionally bound to an "
                        "exact complete purchase list GET with zero records. Raw responses and record IDs remain private."))
    value["evidenceDigest"] = digest(value)
    return value


def _field_value(payload: dict[str, Any], path: str) -> Any:
    parts = path.split("/")[1:]
    if parts[0] in {"scope", "policy"}:
        return payload[parts[0]][parts[1]]
    if parts[0] in {"asOf", "coverageComplete", "mapping"}:
        return payload[parts[0]]
    rows = payload[parts[0]]
    if len(parts) == 1:
        return rows
    row = next(item for item in rows if item["recordId"] == parts[1])
    return row[parts[2]]


def _utc_z(value: str) -> str:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )


def _latest_verified(journal: Journal, resource: str, business_key: str) -> dict[str, Any]:
    row = journal.verified(resource, business_key)
    if row is None:
        raise DatasetError("ERP_VERIFIED_RECORD_MISSING")
    return row


def build_case_package(journal: Journal, seed: dict[str, Any], *, case_id: str,
                       inventory_case_id: str, inventory_available: int,
                       quality_disposition: str = "VERIFIED_CLEAR",
                       purchase_request: dict[str, Any] | None = None) -> dict[str, Any]:
    """Assemble one zero-supply teaching case from fresh GET captures."""

    from commerce_hub.data.admission import (
        ENGINE_SEMANTICS, TeachingAdmissionPackage, teaching_readback_content_digest,
        validate_teaching_admission,
    )
    from commerce_hub.data.contracts import fingerprint

    requests = dataset_requests(seed)
    requests = [(resource, key, ({**request, "quantity": inventory_available,
                                  "available": inventory_available}
                                 if resource == "inventory" else request))
                for resource, key, request in requests]
    rows = [_latest_verified(journal, resource, key) for resource, key, _ in requests]
    empty = (_latest_verified(journal, "purchase-empty", BATCH_ID + "-PURCHASE-A-EMPTY")
             if purchase_request is None else None)
    purchase_row = (_latest_verified(journal, "purchase", purchase_request["order_sn"])
                    if purchase_request is not None else None)
    request_by_key = {(resource, key): request for resource, key, request in requests}
    by_resource: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_resource.setdefault(row["resource"], []).append(row)
    product_row = by_resource["product"][-1]
    listing_row = by_resource["listing"][-1]
    inventory_matches = [row for row in journal.value["records"] if row.get("resource") == "inventory"
                         and row.get("caseId") == inventory_case_id and row.get("state") == "VERIFIED"]
    if not inventory_matches:
        raise DatasetError("ERP_INVENTORY_CASE_MISSING")
    inventory_row = inventory_matches[-1]
    rows = [row for row in rows if row.get("resource") != "inventory"] + [inventory_row]
    if purchase_row is not None:
        rows.append(purchase_row)
    sales_rows = sorted(by_resource["sales"], key=lambda item: item["businessKey"])
    supply_source = purchase_row or empty
    included = [product_row, listing_row, inventory_row, *sales_rows, supply_source]
    raw_by_alias: dict[str, dict[str, Any]] = {}
    for row in included:
        artifact_path = ROOT / row["readBackArtifactRef"]
        raw = artifact_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["readBackRawResponseSHA256"]:
            raise DatasetError("ERP_RAW_ARTIFACT_DIGEST_MISMATCH")
        raw_by_alias[row["businessKeyAlias"]] = json.loads(raw)

    tenant = "s01-eval-" + hashlib.sha256(AUTHORIZATION_ID.encode()).hexdigest()[:32]
    sku = BATCH_ID + "-A"
    canonical_sku = alias("sku", sku)
    store = alias("store", seed["store_id"])
    warehouse = alias("warehouse", seed["wid"])
    scope = dict(tenantId=tenant, canonicalSkuIds=[canonical_sku], storeIds=[store],
                 warehouseIds=[warehouse], fields=["quantity"])
    mapping = dict(version="teaching-map-v1", sourceSku=canonical_sku,
        sourceStore=store, sourceWarehouse=warehouse, canonicalSkuId=canonical_sku,
        storeId=store, warehouseId=warehouse, sourceUnit="EA", unit="EA",
        unitsPerSourceUnit="1")
    inventory_id = inventory_row["recordAlias"]
    inventory_raw = raw_by_alias[inventory_row["businessKeyAlias"]]
    receipt_path = ROOT / inventory_row["writeReceiptRef"]
    receipt_bytes = receipt_path.read_bytes()
    if hashlib.sha256(receipt_bytes).hexdigest() != inventory_row["writeReceiptSHA256"]:
        raise DatasetError("ERP_WRITE_RECEIPT_DIGEST_MISMATCH")
    inventory_receipt = json.loads(receipt_bytes)
    if inventory_receipt.get("updated_at") != inventory_raw.get("updated_at"):
        raise DatasetError("ERP_WRITE_READ_TIMESTAMP_MISMATCH")
    source_updated_at = _utc_z(inventory_raw["updated_at"])
    as_of = max(_utc_z(row["readBackObservedAt"]) for row in included)
    inventory = [dict(recordId=inventory_id, sku=canonical_sku, store=store,
        warehouse=warehouse, unit="EA", availableQty=str(inventory_raw["available"]),
        reservedQty=None, semantics="NET_AVAILABLE", sourceUpdatedAt=source_updated_at)]
    demand = []
    for index, row in enumerate(sales_rows, start=1):
        raw = raw_by_alias[row["businessKeyAlias"]]
        demand.append(dict(recordId=row["recordAlias"], sku=canonical_sku, store=store,
            warehouse=warehouse, unit="EA", day=(date(2026, 11, 12) + timedelta(days=index)).isoformat(),
            quantity=str(raw["item_list"][0]["quantity"]),
            semantics="INCREMENTAL_EXCLUDES_RESERVED"))
    supply = []
    if purchase_row is not None:
        supply_raw = raw_by_alias[purchase_row["businessKeyAlias"]]
        supply = [dict(recordId=purchase_row["recordAlias"],
            supplyId=alias("supply", supply_raw["order_sn"]), sku=canonical_sku,
            store=store, warehouse=warehouse, unit="EA",
            remainingQty=str(purchase_request["item_list"][0]["quantity"]),
            availableDate=purchase_request["planned_arrival"], status="OPEN")]
    policy = dict(version="teaching-s01-rules-v1", horizonDays=7, bufferDays=0,
        maxAgeHours=24, moq="12", orderMultiple="6", candidateDates=["2026-11-19"],
        maxOrderQty="120", otherConstraints="REVIEWED_NOT_APPLICABLE",
        qualityDisposition=quality_disposition)
    payload: dict[str, Any] = dict(scope=scope, asOf=as_of, coverageComplete=True,
        mapping=mapping, inventory=inventory, demand=demand, supply=supply, policy=policy)
    rule_ref = "trusted-artifact:teaching-s01-rules-v1"
    rule_content = dict(scope=scope, appliesAsOf=as_of, policy=policy,
                        engineSemantics=ENGINE_SEMANTICS)
    from commerce_hub.data.admission import RuleContent
    rule_content = RuleContent.model_validate(rule_content).model_dump(mode="json")
    rules = dict(ruleVersion="teaching-s01-rules-v1", contentDigest=fingerprint(rule_content),
        content=rule_content, owner="commerce-hub-teaching", recordRef=rule_ref,
        recordedAt="2026-11-12T00:00:00Z", effectiveFrom="2026-11-01T00:00:00Z",
        effectiveUntil="2026-12-01T00:00:00Z")

    artifact_refs = {row["businessKeyAlias"]: "private-artifact:" + row["businessKeyAlias"]
                     for row in included}
    sales_refs = tuple(artifact_refs[row["businessKeyAlias"]] for row in sales_rows)
    derivation_ref = "trusted-artifact:teaching-last-7-daily-replay-v1-" + case_id
    direct_sources = {
        "/scope/tenantId": inventory_row, "/scope/canonicalSkuIds": product_row,
        "/scope/storeIds": inventory_row, "/scope/warehouseIds": inventory_row,
        "/scope/fields": inventory_row, "/asOf": supply_source, "/coverageComplete": inventory_row,
        "/mapping": listing_row, "/inventory": inventory_row,
        f"/inventory/{inventory_id}/availableQty": inventory_row,
        f"/inventory/{inventory_id}/sourceUpdatedAt": inventory_row,
        f"/inventory/{inventory_id}/semantics": inventory_row,
    }
    if purchase_row is None:
        direct_sources["/supply"] = empty
    else:
        direct_sources[f"/supply/{purchase_row['recordAlias']}/supplyId"] = purchase_row
    provenance: list[dict[str, Any]] = []
    for path, row in direct_sources.items():
        provenance.append(dict(fieldPath=path,
            assertion="COLLECTION_COMPLETE" if path in {"/inventory", "/supply"} else "VALUE_OBSERVED",
            nature="ERP_NETWORK", sourceVersion="teaching-erp-5.1.0",
            owner="commerce-hub-teaching", sourceRef=artifact_refs[row["businessKeyAlias"]],
            observedAt=_utc_z(row["readBackObservedAt"]), valueDigest=fingerprint(_field_value(payload, path)),
            **({"recordCount": len(payload[path[1:]])} if path in {"/inventory", "/supply"} else {})))
    derived_paths = ["/demand"]
    for item in demand:
        derived_paths.extend([f"/demand/{item['recordId']}/{field}"
                              for field in ("day", "quantity", "semantics")])
    derivation_time = max(_utc_z(row["readBackObservedAt"]) for row in sales_rows)
    for path in derived_paths:
        provenance.append(dict(fieldPath=path,
            assertion="COLLECTION_COMPLETE" if path == "/demand" else "VALUE_DERIVED",
            nature="CONTROLLED_TEACHING_RULE", sourceVersion="teaching-s01-rules-v1",
            owner="commerce-hub-teaching", sourceRef=derivation_ref, observedAt=derivation_time,
            valueDigest=fingerprint(_field_value(payload, path)),
            teachingBasis="Controlled replay of seven exact teaching sales GET records onto D1-D7.",
            derivedFromRefs=list(sales_refs),
            **({"recordCount": len(demand)} if path == "/demand" else {})))
    for field in ("horizonDays", "bufferDays", "maxAgeHours", "moq", "orderMultiple",
                  "candidateDates", "maxOrderQty", "otherConstraints", "qualityDisposition"):
        path = "/policy/" + field
        provenance.append(dict(fieldPath=path, assertion="RULE_VALUE",
            nature="CONTROLLED_TEACHING_RULE", sourceVersion="teaching-s01-rules-v1",
            owner="commerce-hub-teaching", sourceRef=rule_ref, observedAt=rules["recordedAt"],
            valueDigest=fingerprint(_field_value(payload, path)),
            teachingBasis="Fixed teaching-only rule; no enterprise business approval."))

    artifacts = []
    all_record_ids = []
    for row in included:
        ref = artifact_refs[row["businessKeyAlias"]]
        record_ids = [] if row["resource"] == "purchase-empty" else [str(row["recordId"])]
        all_record_ids.extend(record_ids)
        fields = sorted(({"fieldPath": item["fieldPath"], "valueDigest": item["valueDigest"]}
            for item in provenance if (item["nature"] == "ERP_NETWORK" and item["sourceRef"] == ref)
            or ref in item.get("derivedFromRefs", [])), key=lambda item: item["fieldPath"])
        artifacts.append(dict(alias=row["businessKeyAlias"], artifactRef=ref,
            operationRef=("openapi:" + row["readBackOperationRef"][len("openapi-"):]
                          if row["readBackOperationRef"].startswith("openapi-")
                          else row["readBackOperationRef"]),
            rawResponseDigest=row["readBackRawResponseSHA256"], observedAt=_utc_z(row["readBackObservedAt"]),
            recordIds=record_ids, contentDigest=fingerprint({"recordIds": sorted(record_ids), "fields": fields})))
    artifact_by_ref = {item["artifactRef"]: item for item in artifacts}
    derivation_content = dict(method="TEACHING_LAST_7_DAILY_REPLAY_V1",
        allowedPaths=derived_paths, sourceArtifactRefs=list(sales_refs),
        sourceContentDigests=[artifact_by_ref[ref]["contentDigest"] for ref in sales_refs],
        teachingRuleRef=rule_ref)
    derivations = [dict(contentDigest=fingerprint(derivation_content), content=derivation_content,
        owner="commerce-hub-teaching", recordRef=derivation_ref, recordedAt=derivation_time)]
    if purchase_row is not None:
        purchase_ref = artifact_refs[purchase_row["businessKeyAlias"]]
        supply_paths = ["/supply"] + [
            f"/supply/{purchase_row['recordAlias']}/{field}"
            for field in ("remainingQty", "availableDate", "status")
        ]
        supply_derivation_ref = "trusted-artifact:teaching-draft-to-planned-supply-v1-" + case_id
        for path in supply_paths:
            provenance.append(dict(fieldPath=path,
                assertion="COLLECTION_COMPLETE" if path == "/supply" else "VALUE_DERIVED",
                nature="CONTROLLED_TEACHING_RULE", sourceVersion="teaching-s01-rules-v1",
                owner="commerce-hub-teaching", sourceRef=supply_derivation_ref,
                observedAt=_utc_z(purchase_row["readBackObservedAt"]),
                valueDigest=fingerprint(_field_value(payload, path)),
                teachingBasis="Teaching draft mapped to planned supply; not a submitted or in-transit order.",
                derivedFromRefs=[purchase_ref],
                **({"recordCount": 1} if path == "/supply" else {})))
        purchase_artifact = artifact_by_ref[purchase_ref]
        # Rebind after adding derived provenance fields supported by the draft artifact.
        fields = sorted(({"fieldPath": item["fieldPath"], "valueDigest": item["valueDigest"]}
            for item in provenance if (item["nature"] == "ERP_NETWORK" and item["sourceRef"] == purchase_ref)
            or purchase_ref in item.get("derivedFromRefs", [])), key=lambda item: item["fieldPath"])
        purchase_artifact["contentDigest"] = fingerprint({
            "recordIds": sorted(purchase_artifact["recordIds"]), "fields": fields})
        supply_content = dict(method="TEACHING_DRAFT_TO_PLANNED_SUPPLY_V1",
            allowedPaths=supply_paths, sourceArtifactRefs=[purchase_ref],
            sourceContentDigests=[purchase_artifact["contentDigest"]], teachingRuleRef=rule_ref)
        derivations.append(dict(contentDigest=fingerprint(supply_content), content=supply_content,
            owner="commerce-hub-teaching", recordRef=supply_derivation_ref,
            recordedAt=_utc_z(purchase_row["readBackObservedAt"])))
    aggregate_write = fingerprint(sorted(row.get("writeArtifactDigest") or row["requestDigest"]
                                         for row in rows))
    seed_digest = inventory_row["readScopeDigest"]
    batch = dict(batchId=BATCH_ID, writeBatchId=BATCH_ID, readBackBatchId=BATCH_ID,
        writeOperationRef=f"openapi:5.1.0/20260917-teaching-final-v2/aggregate-write/S01-{case_id}",
        writeReceiptRef=f"private-artifact:aggregate-write-receipts-{case_id}",
        writeReceiptDigest=fingerprint(sorted(row.get("writeReceiptSHA256") or row["requestDigest"]
                                              for row in rows)),
        writeArtifactDigest=aggregate_write, writeCanonicalContentDigest="0" * 64,
        readBackOperationRef=f"openapi:5.1.0/20260917-teaching-final-v2/aggregate-readback/S01-{case_id}",
        readBackArtifactRef=f"private-artifact:aggregate-readback-manifest-{case_id}",
        readBackArtifactDigest="0" * 64, readBackObservedAt=as_of,
        readBackArtifacts=artifacts, writeScopeDigest=seed_digest, readBackScopeDigest=seed_digest,
        canonicalScopeDigest=fingerprint(scope), writeRecordIds=sorted(all_record_ids),
        readBackRecordIds=sorted(all_record_ids), readBackContentDigest="0" * 64)
    package = dict(packageVersion="s01-teaching-admission-package-v1",
        admissionMode="TEACHING_SIMULATION", sourceNature=SOURCE_NATURE,
        inputId=f"s01-teaching-{case_id}", fixtureId=f"s01-teaching-{case_id}", assembledAt=as_of,
        **payload, provenance=provenance, teachingBatch=batch, rules=rules, derivations=derivations)
    package["teachingBatch"]["readBackContentDigest"] = teaching_readback_content_digest(package)
    inventory_request = request_by_key[("inventory", inventory_row["businessKey"])]
    if digest(inventory_request) != inventory_row["requestDigest"]:
        raise DatasetError("ERP_WRITE_REQUEST_DIGEST_MISMATCH")
    write_demand = []
    for index, row in enumerate(sales_rows, start=1):
        request = request_by_key[("sales", row["businessKey"])]
        if digest(request) != row["requestDigest"]:
            raise DatasetError("ERP_WRITE_REQUEST_DIGEST_MISMATCH")
        write_demand.append(dict(recordId=row["recordAlias"], sku=canonical_sku, store=store,
            warehouse=warehouse, unit="EA", day=(date(2026, 11, 12) + timedelta(days=index)).isoformat(),
            quantity=str(request["item_list"][0]["quantity"]),
            semantics="INCREMENTAL_EXCLUDES_RESERVED"))
    write_supply = [] if purchase_request is None else [dict(recordId=purchase_row["recordAlias"],
        supplyId=alias("supply", purchase_request["order_sn"]), sku=canonical_sku, store=store,
        warehouse=warehouse, unit="EA", remainingQty=str(purchase_request["item_list"][0]["quantity"]),
        availableDate=purchase_request["planned_arrival"], status="OPEN")]
    if purchase_request is not None and digest(purchase_request) != purchase_row["requestDigest"]:
        raise DatasetError("ERP_WRITE_REQUEST_DIGEST_MISMATCH")
    write_canonical = dict(batchId=BATCH_ID, scope=scope, asOf=as_of, coverageComplete=True,
        mapping=mapping, inventory=[dict(recordId=inventory_id, sku=canonical_sku, store=store,
            warehouse=warehouse, unit="EA", availableQty=str(inventory_request["available"]),
            reservedQty=None, semantics="NET_AVAILABLE", sourceUpdatedAt=source_updated_at)],
        demand=write_demand, supply=write_supply)
    package["teachingBatch"]["writeCanonicalContentDigest"] = fingerprint(write_canonical)
    if (package["teachingBatch"]["writeCanonicalContentDigest"]
            != package["teachingBatch"]["readBackContentDigest"]):
        raise DatasetError("ERP_WRITE_READ_CANONICAL_CONTENT_MISMATCH")
    manifest_time = as_of
    package["teachingBatch"]["readBackArtifactDigest"] = fingerprint({
        "batchId": BATCH_ID, "operationRef": batch["readBackOperationRef"], "observedAt": manifest_time,
        "artifacts": sorted(artifacts, key=lambda item: item["alias"]),
    })
    validated = TeachingAdmissionPackage.model_validate(package)
    decision = validate_teaching_admission(validated)
    if not decision.admitted:
        raise DatasetError("TEACHING_ADMISSION_BLOCKED:" + ",".join(
            issue.code + "@" + issue.path for issue in decision.issues
        ))
    return validated.model_dump(mode="json")


def derive_policy_case(base: dict[str, Any], *, case_id: str,
                       policy_overrides: dict[str, Any]) -> dict[str, Any]:
    """Reuse A's GET facts while changing only an explicit teaching rule record."""

    from copy import deepcopy
    from commerce_hub.data.admission import (
        RuleContent, TeachingAdmissionPackage, validate_teaching_admission,
    )
    from commerce_hub.data.contracts import fingerprint

    value = deepcopy(base)
    value["inputId"] = value["fixtureId"] = "s01-teaching-" + case_id
    value["policy"].update(policy_overrides)
    value["rules"]["content"]["policy"] = deepcopy(value["policy"])
    rule_content = RuleContent.model_validate(value["rules"]["content"]).model_dump(mode="json")
    value["rules"]["content"] = rule_content
    value["rules"]["contentDigest"] = fingerprint(rule_content)
    for item in value["provenance"]:
        if item["fieldPath"].startswith("/policy/"):
            item["valueDigest"] = fingerprint(_field_value(value, item["fieldPath"]))
        if item["sourceRef"].startswith("trusted-artifact:teaching-last-7-daily-replay-v1-"):
            item["sourceRef"] = "trusted-artifact:teaching-last-7-daily-replay-v1-" + case_id
    for derivation in value["derivations"]:
        if derivation["content"]["method"] == "TEACHING_LAST_7_DAILY_REPLAY_V1":
            derivation["recordRef"] = "trusted-artifact:teaching-last-7-daily-replay-v1-" + case_id
    batch = value["teachingBatch"]
    batch["writeOperationRef"] = f"openapi:5.1.0/20260917-teaching-final-v2/aggregate-write/S01-{case_id}"
    batch["writeReceiptRef"] = f"private-artifact:aggregate-write-receipts-{case_id}"
    batch["readBackOperationRef"] = f"openapi:5.1.0/20260917-teaching-final-v2/aggregate-readback/S01-{case_id}"
    batch["readBackArtifactRef"] = f"private-artifact:aggregate-readback-manifest-{case_id}"
    batch["readBackArtifactDigest"] = fingerprint({
        "batchId": batch["readBackBatchId"], "operationRef": batch["readBackOperationRef"],
        "observedAt": _utc_z(str(batch["readBackObservedAt"])),
        "artifacts": sorted(batch["readBackArtifacts"], key=lambda item: item["alias"]),
    })
    validated = TeachingAdmissionPackage.model_validate(value)
    decision = validate_teaching_admission(validated)
    if not decision.admitted:
        raise DatasetError("TEACHING_ADMISSION_BLOCKED:" + ",".join(issue.code for issue in decision.issues))
    return validated.model_dump(mode="json")


def config_from_env() -> Config:
    values = dotenv_values(ROOT / ".env.erp", interpolate=False)
    if (values.get("ERP_BASE_URL") or BASE_URL) != BASE_URL:
        raise DatasetError("ERP_BASE_URL_REJECTED")
    return Config(username=values.get("ERP_USERNAME") or "", password=values.get("ERP_PASSWORD") or "",
                  access_token=values.get("ERP_ACCESS_TOKEN") or "")


def run(*, phase: str = "ALL", run_dir: Path | None = None,
        execute_teaching_data: bool = False) -> tuple[dict[str, Any], Path]:
    if execute_teaching_data is not True:
        raise DatasetError("TEACHING_DATA_EXECUTION_NOT_ENABLED")
    if phase not in {"A", "ALL"}:
        raise DatasetError("INVALID_PHASE")
    run_dir = run_dir or PRIVATE_ROOT / BATCH_ID
    journal = Journal(run_dir / "journal.json")
    client = TeachingDatasetClient(config_from_env(), run_dir / "raw")
    seed = discover_scope(client)
    seed_sha = scope_digest(seed)
    requests = dataset_requests(seed)
    selected = requests
    for resource, key, request in selected:
        verify_or_create(client, journal, resource, key, request, seed_sha)
    inventory_request = next(request for resource, _, request in selected if resource == "inventory")
    capture_inventory_case(client, journal, inventory_request, seed_sha, "A")
    refresh_verified_readbacks(client, journal, selected, seed_sha)
    verify_empty_purchase_collection(client, journal, seed_sha, refresh=True)
    verify_scope_collections(client, journal, seed_sha, refresh=True)
    evidence = public_evidence(journal, seed_sha)
    case_a = build_case_package(journal, seed, case_id="A", inventory_case_id="A",
                                inventory_available=60)
    case_dir = run_dir / "cases/A"
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "package.json").write_bytes(
        json.dumps(case_a, ensure_ascii=False, indent=2, default=str).encode("utf-8") + b"\n")
    PUBLIC_ROOT.mkdir(parents=True, exist_ok=True)
    (PUBLIC_ROOT / "dataset-evidence.json").write_bytes(
        json.dumps(evidence, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    review = dict(schemaVersion="s01-teaching-case-review-v1", caseId="A", result="ADMITTED",
        sourceNature=SOURCE_NATURE, batchId=BATCH_ID, openingAvailable="60",
        demandRule="TEACHING_LAST_7_DAILY_REPLAY_V1", demand=[8, 10, 9, 11, 12, 14, 13],
        supplyEvidence="EXACT_BATCH_MATCH_COMPLETE_EMPTY_SET", supplyRecordCount=0,
        supplyBoundary=("The empty batch-order query proves only the teaching rule's designated supply set; "
                        "it does not prove all real outstanding supply for the SKU is zero."),
        inventoryCollection="EXACT_SCOPE_COMPLETE_SINGLE_ROW",
        salesCollection="EXACT_SCOPE_COMPLETE_SEVEN_UNIQUE_ORDERS",
        golden=dict(baselineBalances=[52, 42, 33, 22, 10, -4, -17], gapQuantity=17,
            firstStockoutDay=6, candidateQuantity=18, candidateArrivalDay=7,
            candidateBalances=[52, 42, 33, 22, 10, -4, 1], candidateFirstStockoutDay=6,
            constraintOutcome="CANDIDATE_STILL_HAS_INTERMEDIATE_SHORTAGE", maxOrderQty=120),
        sourceUpdatedAtBasis="ERP_WRITE_RECEIPT_AND_DETAIL_GET_MATCH",
        writeReadCanonicalComparison="INDEPENDENT_MATCH",
        packageDigest=digest(case_a), privateArtifactRef="private-artifact:case-A-package",
        rawIdentifiersPublished=False, modelCalls=0)
    review["evidenceDigest"] = digest(review)
    (PUBLIC_ROOT / "case-A-review.json").write_bytes(
        json.dumps(review, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    if phase == "ALL":
        b_inventory = {**inventory_request, "quantity": 96, "available": 96}
        capture_inventory_case(client, journal, b_inventory, seed_sha, "B")
        case_b = build_case_package(journal, seed, case_id="B", inventory_case_id="B",
                                    inventory_available=96)
        b_dir = run_dir / "cases/B"
        b_dir.mkdir(parents=True, exist_ok=True)
        (b_dir / "package.json").write_bytes(
            json.dumps(case_b, ensure_ascii=False, indent=2, default=str).encode("utf-8") + b"\n")
        b_review = dict(schemaVersion="s01-teaching-case-review-v1", caseId="B", result="ADMITTED",
            sourceNature=SOURCE_NATURE, batchId=BATCH_ID, openingAvailable="96",
            demandRule="TEACHING_LAST_7_DAILY_REPLAY_V1", demand=[8, 10, 9, 11, 12, 14, 13],
            supplyEvidence="EXACT_BATCH_MATCH_COMPLETE_EMPTY_SET", supplyRecordCount=0,
            inventoryCollection="EXACT_SCOPE_COMPLETE_SINGLE_ROW",
            salesCollection="SEVEN_EXACT_KEYS_COMPLETE_NO_MIRRORS",
            golden=dict(baselineBalances=[88, 78, 69, 58, 46, 32, 19], gapQuantity=0,
                firstStockoutDay=None, candidateQuantity=None,
                constraintOutcome="NO_REPLENISHMENT_NEEDED"),
            actualErpEvidence="OWNED_INVENTORY_PUT_AND_DETAIL_GET",
            sourceUpdatedAtBasis="ERP_WRITE_RECEIPT_AND_DETAIL_GET_MATCH",
            writeReadCanonicalComparison="INDEPENDENT_MATCH",
            packageDigest=digest(case_b), privateArtifactRef="private-artifact:case-B-package",
            rawIdentifiersPublished=False, modelCalls=0)
        b_review["evidenceDigest"] = digest(b_review)
        (PUBLIC_ROOT / "case-B-review.json").write_bytes(
            json.dumps(b_review, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
        c_inventory = {**inventory_request, "quantity": 10, "available": 10}
        capture_inventory_case(client, journal, c_inventory, seed_sha, "C")
        c_purchase = purchase_c_request(seed)
        verify_or_create(client, journal, "purchase", c_purchase["order_sn"], c_purchase, seed_sha)
        case_c = build_case_package(journal, seed, case_id="C", inventory_case_id="C",
                                    inventory_available=10, purchase_request=c_purchase)
        c_dir = run_dir / "cases/C"
        c_dir.mkdir(parents=True, exist_ok=True)
        (c_dir / "package.json").write_bytes(
            json.dumps(case_c, ensure_ascii=False, indent=2, default=str).encode("utf-8") + b"\n")
        c_review = dict(schemaVersion="s01-teaching-case-review-v1", caseId="C", result="ADMITTED",
            sourceNature=SOURCE_NATURE, batchId=BATCH_ID, openingAvailable="10",
            demandRule="TEACHING_LAST_7_DAILY_REPLAY_V1",
            supplyRule="TEACHING_DRAFT_TO_PLANNED_SUPPLY_V1",
            supplyBoundary="Draft teaching record only; not submitted, ordered, approved, or in transit.",
            inventoryCollection="EXACT_SCOPE_COMPLETE_SINGLE_ROW",
            salesCollection="SEVEN_EXACT_KEYS_COMPLETE_NO_MIRRORS",
            golden=dict(baselineBalances=[2, -8, -17, -28, -40, -54, 0], gapQuantity=0,
                firstStockoutDay=2, constraintOutcome="INTERMEDIATE_SHORTAGE_POLICY_UNDEFINED"),
            actualErpEvidence="OWNED_INVENTORY_AND_PURCHASE_DRAFT_PUT_OR_POST_PLUS_DETAIL_GET",
            sourceUpdatedAtBasis="ERP_INVENTORY_WRITE_RECEIPT_AND_DETAIL_GET_MATCH",
            writeReadCanonicalComparison="INDEPENDENT_MATCH_INVENTORY_SALES_AND_PURCHASE_DRAFT_REQUESTS",
            packageDigest=digest(case_c), privateArtifactRef="private-artifact:case-C-package",
            rawIdentifiersPublished=False, modelCalls=0)
        c_review["evidenceDigest"] = digest(c_review)
        (PUBLIC_ROOT / "case-C-review.json").write_bytes(
            json.dumps(c_review, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
        d_case = derive_policy_case(case_a, case_id="D", policy_overrides={
            "candidateDates": ["2026-11-13"], "maxOrderQty": "17"})
        d_dir = run_dir / "cases/D"; d_dir.mkdir(parents=True, exist_ok=True)
        (d_dir / "package.json").write_bytes(
            json.dumps(d_case, ensure_ascii=False, indent=2, default=str).encode("utf-8") + b"\n")
        d_review = dict(schemaVersion="s01-teaching-case-review-v1", caseId="D", result="ADMITTED",
            actualErpEvidence="REUSES_CASE_A_GET_FACTS", policyEvidence="CONTROLLED_TEACHING_RULE_ONLY",
            inventoryCollection="REUSES_A_EXACT_SCOPE_COMPLETE_SINGLE_ROW",
            salesCollection="REUSES_A_SEVEN_EXACT_KEYS_COMPLETE_NO_MIRRORS",
            sourceUpdatedAtBasis="REUSES_A_ERP_WRITE_RECEIPT_AND_DETAIL_GET_MATCH",
            writeReadCanonicalComparison="INDEPENDENT_MATCH_REUSED_FROM_A_FACT_SET",
            selectedCatalogVariant="D-MAX", golden=dict(candidateQuantity=18, maxOrderQty=17,
                constraintOutcome="NO_FEASIBLE_QUANTITY"), variants={
                "D-MOQ": {"moq": 24, "orderMultiple": 6, "candidateDay": 1,
                          "candidateQuantity": 24, "basis": "CONTROLLED_GOLDEN_RECALCULATION"},
                "D-MULTIPLE": {"moq": 12, "orderMultiple": 10, "candidateDay": 1,
                               "candidateQuantity": 20, "basis": "CONTROLLED_GOLDEN_RECALCULATION"},
                "D-MAX": {"maxOrderQty": 17, "candidateQuantity": 18,
                          "constraintOutcome": "NO_FEASIBLE_QUANTITY",
                          "basis": "CONTROLLED_GOLDEN_RECALCULATION"},
                "D-AVAILABLE-DATE": {"candidateDay": 7, "candidateFirstStockoutDay": 6,
                                     "basis": "CONTROLLED_GOLDEN_RECALCULATION"}},
            packageDigest=digest(d_case), privateArtifactRef="private-artifact:case-D-package",
            rawIdentifiersPublished=False, modelCalls=0)
        d_review["evidenceDigest"] = digest(d_review)
        (PUBLIC_ROOT / "case-D-review.json").write_bytes(
            json.dumps(d_review, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")

        quality_request = next(request for resource, _, request in selected if resource == "quality")
        abnormal_quality = {**quality_request, "available_qty": 19, "defective_qty": 1,
                            "qc_status": "TEACHING_QUALITY_INVESTIGATE"}
        abnormal_quality["item_list"] = [{**quality_request["item_list"][0],
                                           "available_qty": 19, "defective_qty": 1}]
        verify_or_create(client, journal, "quality", abnormal_quality["order_sn"], abnormal_quality, seed_sha)
        e_case = derive_policy_case(case_a, case_id="E", policy_overrides={
            "qualityDisposition": "INVESTIGATE"})
        e_dir = run_dir / "cases/E"; e_dir.mkdir(parents=True, exist_ok=True)
        (e_dir / "package.json").write_bytes(
            json.dumps(e_case, ensure_ascii=False, indent=2, default=str).encode("utf-8") + b"\n")
        e_review = dict(schemaVersion="s01-teaching-case-review-v1", caseId="E", result="ADMITTED",
            selectedCatalogVariant="E-QUALITY",
            actualErpEvidence="OWNED_QUALITY_RECORD_PUT_AND_DETAIL_GET_INVESTIGATE",
            actualQualityGet=dict(qcStatus="TEACHING_QUALITY_INVESTIGATE", inspectedQty=20,
                                  availableQty=19, defectiveQty=1),
            inventoryCollection="REUSES_A_EXACT_SCOPE_COMPLETE_SINGLE_ROW",
            salesCollection="REUSES_A_SEVEN_EXACT_KEYS_COMPLETE_NO_MIRRORS",
            policyEvidence="CONTROLLED_TEACHING_RULE_BOUND_TO_INVESTIGATE_DISPOSITION",
            sourceUpdatedAtBasis="REUSES_A_ERP_WRITE_RECEIPT_AND_DETAIL_GET_MATCH",
            writeReadCanonicalComparison="INDEPENDENT_MATCH_REUSED_FROM_A_FACT_SET",
            qualityAuditBoundary=("The INVESTIGATE quality PUT+GET is separate actual ERP audit evidence; "
                                  "the admitted quantity package binds the controlled quality rule."),
            golden=dict(constraintOutcome="QUALITY_REQUIRES_RESOLUTION", candidateQuantity=None),
            variants={"E-DATA": {"openingAvailable": None, "status": "INSUFFICIENT_DATA",
                "basis": "OFFLINE_GOLDEN_ONLY_NOT_ERP_MISSING_FACT"},
                "E-QUALITY": {"qualityDisposition": "INVESTIGATE",
                    "basis": "ACTUAL_TEACHING_ERP_QUALITY_GET_PLUS_CONTROLLED_RULE"}},
            packageDigest=digest(e_case), privateArtifactRef="private-artifact:case-E-package",
            rawIdentifiersPublished=False, modelCalls=0)
        e_review["evidenceDigest"] = digest(e_review)
        (PUBLIC_ROOT / "case-E-review.json").write_bytes(
            json.dumps(e_review, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")

        tenant = "s01-eval-" + hashlib.sha256(AUTHORIZATION_ID.encode()).hexdigest()[:32]
        cases = {"A": case_a, "B": case_b, "C": case_c, "D": d_case, "E": e_case}
        catalog = dict(schemaVersion="s01-model-evaluation-catalog-v1",
            authorizationId=AUTHORIZATION_ID, tenantId=tenant,
            entries=[dict(caseId=key, kind="TEACHING_SIMULATION", payload=value)
                     for key, value in cases.items()])
        (run_dir / "catalog.json").write_bytes(
            json.dumps(catalog, ensure_ascii=False, indent=2, default=str).encode("utf-8") + b"\n")
        catalog_review = dict(schemaVersion="s01-model-evaluation-catalog-review-v1",
            authorizationId=AUTHORIZATION_ID, tenantId=tenant, caseIds=list("ABCDE"),
            packageDigests={key: digest(value) for key, value in cases.items()},
            sourceKinds={"A": "ACTUAL_ERP", "B": "ACTUAL_ERP", "C": "ACTUAL_ERP_DRAFT",
                         "D": "A_GET_PLUS_CONTROLLED_RULE", "E": "A_GET_PLUS_QUALITY_GET_AND_RULE"},
            canonicalAudit={key: "INDEPENDENT_WRITE_READ_MATCH" for key in cases},
            sourceUpdatedAtAudit={
                "A": "ERP_RECEIPT_EQUALS_DETAIL_GET", "B": "ERP_RECEIPT_EQUALS_DETAIL_GET",
                "C": "ERP_RECEIPT_EQUALS_DETAIL_GET", "D": "REUSES_A_VERIFIED_FACT",
                "E": "REUSES_A_VERIFIED_FACT"},
            modelCalls=0, rawIdentifiersPublished=False)
        catalog_review["evidenceDigest"] = digest(catalog_review)
        (PUBLIC_ROOT / "catalog-review.json").write_bytes(
            json.dumps(catalog_review, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
        golden = dict(schemaVersion="s01-teaching-golden-v1", cases={
            "A": review["golden"], "B": b_review["golden"], "C": c_review["golden"],
            "D": d_review["golden"], "E": e_review["golden"]},
            subcases={"D": d_review["variants"], "E": e_review["variants"]}, modelCalls=0)
        golden["evidenceDigest"] = digest(golden)
        (PUBLIC_ROOT / "teaching-golden.json").write_bytes(
            json.dumps(golden, ensure_ascii=False, indent=2).encode("utf-8") + b"\n")
    return evidence, journal.path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["A", "ALL"], default="ALL")
    parser.add_argument("--execute-teaching-data", action="store_true")
    args = parser.parse_args()
    if not args.execute_teaching_data:
        print(json.dumps(dict(result="NOT_RUN", batchId=BATCH_ID,
                              code="TEACHING_DATA_EXECUTION_NOT_ENABLED")))
        return 0
    try:
        evidence, journal_path = run(phase=args.phase, execute_teaching_data=True)
        print(json.dumps(dict(result=evidence["result"], batchId=BATCH_ID,
            verified=sum(evidence["resourceCounts"].values()), evidenceDigest=evidence["evidenceDigest"],
            privateJournal=journal_path.relative_to(ROOT).as_posix())))
        return 0
    except DatasetError as error:
        print(json.dumps(dict(result="BLOCKED" if error.code == "ERP_SCOPE_DENIED" else "FAIL",
                              batchId=BATCH_ID, code=error.code)))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
