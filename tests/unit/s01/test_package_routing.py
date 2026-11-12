"""Bound fixed-package workers to their actual source bundle."""
from types import SimpleNamespace

from commerce_hub.bootstrap.teaching_erp import registry as teaching_registry
from commerce_hub.bootstrap.s01_backend import registry as backend_registry
from tests.support.teaching import observed_fixture
from tests.support.backend import cases


def settings():
    return SimpleNamespace(environment="test", model_provider="mock", model_network_enabled=False,
        model_timeout_seconds=15, auth_issuer="test-issuer", auth_audience="test-audience")


def test_teaching_packages_have_distinct_durable_routes():
    one = observed_fixture()
    two = observed_fixture(dict(tenantId="other", storeIds=["store-fixture"], warehouseIds=["warehouse-fixture"],
        canonicalSkuIds=["sku-fixture"], fields=["quantity"]))
    first = teaching_registry(settings(), one)["TEACHING_S01_ADMISSION"].work_kind
    second = teaching_registry(settings(), two)["TEACHING_S01_ADMISSION"].work_kind
    assert first != second and len(first) <= 64 and len(second) <= 64
    assert teaching_registry(settings(), one)["TEACHING_S01_ADMISSION"].work_kind == first


def test_backend_catalogs_have_distinct_routes_and_restarts_are_stable():
    one = backend_registry(settings(), [cases()["A"]])["S01_BACKEND"].work_kind
    two = backend_registry(settings(), [cases()["B"]])["S01_BACKEND"].work_kind
    assert one != two and len(one) <= 64 and len(two) <= 64
    assert backend_registry(settings(), [cases()["A"]])["S01_BACKEND"].work_kind == one
