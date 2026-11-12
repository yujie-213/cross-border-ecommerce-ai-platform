from pathlib import Path

import pytest

from tools.s01_teaching_dataset import (
    BATCH_ID, Config, Journal, DatasetError, TeachingDatasetClient, business_content, dataset_requests, digest,
    operation_ref, public_evidence, refresh_verified_readbacks, run, verify_empty_purchase_collection,
    verify_or_create,
)


class Client:
    def __init__(self, existing=None):
        self.existing = existing or {}
        self.calls = []
        self.next_id = 100

    def exact(self, resource, field, value):
        self.calls.append(("EXACT", resource, field, value))
        return self.existing.get((resource, value), [])

    def authorize_owned(self, resource, record_id):
        self.calls.append(("OWNED", resource, record_id))

    def request(self, method, path, values=None):
        self.calls.append((method, path, values))
        if method == "POST":
            self.next_id += 1
            return {"id": self.next_id, **values}, "a" * 64, "2026-11-12T00:00:00+00:00", "private/receipt"
        record = next(call[2] for call in self.calls if call[0] == "POST")
        return ({"id": self.next_id, "tenant_id": 1, **record,
                 "created_at": "x", "updated_at": "y"}, "b" * 64,
                "2026-11-12T00:00:01+00:00", "private/readback")


def seed():
    return dict(store_id=1, store_name="Authorized Store", wid=2, warehouse_name="Authorized Warehouse")


def test_dataset_contains_only_documented_crud_records_and_batch_keys():
    values = dataset_requests(seed())
    assert len(values) == 11
    assert [x[0] for x in values].count("sales") == 7
    assert all(BATCH_ID in key for _, key, _ in values)
    sales = next(value for kind, _, value in values if kind == "sales")
    assert "status_text" not in sales and "tracking_no" not in sales
    quality = next(value for kind, _, value in values if kind == "quality")
    assert quality["qc_status"] == "TEACHING_QUALITY_CLEAR" and quality["defective_qty"] == 0
    a_inventory = next(value for kind, key, value in values if kind == "inventory" and key.endswith("-INV-A"))
    assert a_inventory["available"] == 60


def test_post_is_journaled_then_verified_by_independent_get(tmp_path):
    journal = Journal(tmp_path / "journal.json")
    client = Client()
    request = dict(sku=BATCH_ID + "-A", name="sample")
    value = verify_or_create(client, journal, "product", request["sku"], request, "scope-digest")
    assert value["state"] == "VERIFIED"
    assert [x[0] for x in client.calls] == ["EXACT", "POST", "GET"]
    assert value["writeArtifactDigest"] == digest(request)
    assert value["readBackContentDigest"] == digest(request)
    assert "get_products" in value["readBackOperationRef"]


def test_readback_mismatch_fails_closed(tmp_path):
    class Bad(Client):
        def request(self, method, path, values=None):
            result = super().request(method, path, values)
            if method == "GET":
                result[0]["name"] = "changed"
            return result
    journal = Journal(tmp_path / "journal.json")
    with pytest.raises(DatasetError, match="ERP_READBACK_CONTENT_MISMATCH"):
        verify_or_create(Bad(), journal, "product", BATCH_ID + "-A",
                         dict(sku=BATCH_ID + "-A", name="sample"), "scope")
    assert journal.value["records"][-1]["state"] == "FAILED"


def test_existing_verified_record_is_idempotent_without_network(tmp_path):
    journal = Journal(tmp_path / "journal.json")
    request = dict(sku=BATCH_ID + "-A")
    journal.append(dict(resource="product", businessKey=BATCH_ID + "-A", state="VERIFIED",
                        requestDigest=digest(request)))
    client = Client()
    value = verify_or_create(client, journal, "product", BATCH_ID + "-A",
                             request, "scope")
    assert value["state"] == "VERIFIED" and client.calls == []


def test_unresolved_send_is_never_blindly_retried(tmp_path):
    journal = Journal(tmp_path / "journal.json")
    journal.append(dict(resource="product", businessKey=BATCH_ID + "-A", state="UNKNOWN"))
    client = Client()
    with pytest.raises(DatasetError, match="ERP_PREVIOUS_SEND_UNRESOLVED"):
        verify_or_create(client, journal, "product", BATCH_ID + "-A",
                         dict(sku=BATCH_ID + "-A"), "scope")
    assert client.calls == []


def test_run_requires_explicit_teaching_data_execution_flag():
    with pytest.raises(DatasetError, match="TEACHING_DATA_EXECUTION_NOT_ENABLED"):
        run()


def test_empty_purchase_supply_requires_exact_complete_list_get(tmp_path):
    class EmptyPurchaseClient:
        calls = []

        def request(self, method, path, values=None):
            self.calls.append((method, path, values))
            return ({"items": [], "total": 0}, "e" * 64,
                    "2026-11-12T00:00:00+00:00", "private/empty-purchase")

    journal = Journal(tmp_path / "journal.json")
    client = EmptyPurchaseClient()
    value = verify_empty_purchase_collection(client, journal, "scope")
    assert client.calls == [("GET", "/api/v1/purchase-orders", {
        "order_sn": BATCH_ID + "-PURCHASE-A", "match": "exact", "offset": 0, "limit": 20})]
    assert value["state"] == "VERIFIED" and value["recordIds"] == []
    assert value["recordCount"] == 0 and value["completeness"] == "EXACT_BATCH_MATCH_COMPLETE"


def test_nonempty_purchase_list_cannot_prove_zero_supply(tmp_path):
    class NonemptyPurchaseClient:
        def request(self, method, path, values=None):
            return ({"items": [{"id": 1}], "total": 1}, "e" * 64,
                    "2026-11-12T00:00:00+00:00", "private/nonempty-purchase")

    with pytest.raises(DatasetError, match="ERP_PURCHASE_EMPTY_SET_NOT_PROVEN"):
        verify_empty_purchase_collection(NonemptyPurchaseClient(), Journal(tmp_path / "journal.json"), "scope")


def test_raw_response_numbering_continues_across_processes(tmp_path):
    (tmp_path / "response-007.json").write_text("{}", encoding="utf-8")
    client = TeachingDatasetClient(Config(username="offline", password="offline"), tmp_path)
    assert client.serial == 7


def test_verified_readback_refresh_is_get_only_and_rebinds_raw_digest(tmp_path):
    request = dict(sku=BATCH_ID + "-A", name="sample")
    journal = Journal(tmp_path / "journal.json")
    journal.append(dict(resource="product", businessKey=request["sku"], state="VERIFIED",
                        recordId=123, requestDigest=digest(request)))

    class RefreshClient:
        calls = []

        def request(self, method, path, values=None):
            self.calls.append((method, path, values))
            return ({"id": 123, **request}, "f" * 64,
                    "2026-11-12T00:01:00+00:00", "private/refreshed")

    client = RefreshClient()
    refresh_verified_readbacks(client, journal, [("product", request["sku"], request)], "scope")
    row = journal.value["records"][0]
    assert client.calls == [("GET", "/api/v1/products/123", None)]
    assert row["readBackArtifactRef"] == "private/refreshed"
    assert row["readBackRawResponseSHA256"] == "f" * 64


@pytest.mark.parametrize(("method", "path"), [
    ("POST", "/api/v1/workflows/purchase-orders/1/submit"),
    ("POST", "/api/v1/stock/inbound-orders/confirm"),
    ("POST", "/api/v1/sales-workflow/1/record-payment"),
    ("GET", "https://evil.invalid/api/v1/products"),
    ("GET", "/api/v1/products/../purchase-orders"),
    ("DELETE", "/api/v1/sales-orders/1"),
])
def test_request_layer_rejects_workflows_external_urls_and_sales_delete_before_transport(tmp_path, method, path):
    client = TeachingDatasetClient(Config(username="offline", password="offline"), tmp_path)
    client.token = "offline"
    client.authorize_owned("sales-orders", 1)
    with pytest.raises(DatasetError, match="ERP_OPERATION_NOT_ALLOWLISTED"):
        client.request(method, path, {})


def test_public_evidence_excludes_business_keys_ids_and_private_refs(tmp_path):
    journal = Journal(tmp_path / "journal.json")
    journal.append(dict(resource="product", businessKey=BATCH_ID + "-A",
        businessKeyAlias="product-abc", state="VERIFIED", recordId=123, recordAlias="record-abc",
        writeOperationRef=operation_ref("create_products", "products"),
        readBackOperationRef=operation_ref("get_products", "products", 123),
        writeReceiptRef="private/receipt", readBackArtifactRef="private/readback",
        writeReceiptSHA256="a"*64, writeArtifactDigest="b"*64,
        readBackRawResponseSHA256="c"*64, readBackObservedAt="2026-11-12T00:00:00Z",
        readBackContentDigest="d"*64, writeScopeDigest="s", readScopeDigest="s"))
    evidence = public_evidence(journal, "s")
    text = str(evidence)
    assert BATCH_ID + "-A" not in text and "private/" not in text and "123" not in text
    assert evidence["records"][0]["recordAlias"] == "record-abc"


def test_business_content_uses_only_requested_fields():
    request = {"sku": "A", "name": "B"}
    record = {**request, "id": 1, "tenant_id": 2, "created_at": "x", "unexpected": "secret"}
    assert business_content(record, request) == request


@pytest.mark.parametrize("page", [
    {"items": [], "total": True},
    {"items": [], "total": -1},
    {"items": "not-a-list", "total": 0},
])
def test_exact_rejects_invalid_page_before_any_create(tmp_path, page):
    client = TeachingDatasetClient(Config(username="offline", password="offline"), tmp_path)
    client.request = lambda *args, **kwargs: (page, "a" * 64, "2026-11-12T00:00:00Z", "private/page")
    with pytest.raises(DatasetError, match="ERP_INVALID_PAGE"):
        client.exact("products", "sku", BATCH_ID + "-A")


@pytest.mark.parametrize("page", [
    {"items": [], "total": 1},
    {"items": [{"id": index} for index in range(20)], "total": 21},
])
def test_exact_rejects_incomplete_page_before_any_create(tmp_path, page):
    client = TeachingDatasetClient(Config(username="offline", password="offline"), tmp_path)
    client.request = lambda *args, **kwargs: (page, "a" * 64, "2026-11-12T00:00:00Z", "private/page")
    with pytest.raises(DatasetError, match="ERP_PAGINATION_INCOMPLETE"):
        client.exact("products", "sku", BATCH_ID + "-A")
