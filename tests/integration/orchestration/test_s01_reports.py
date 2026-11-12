"""Actual isolated MySQL tests; every tenant and delivery kind is test-owned."""
from copy import deepcopy
from datetime import timedelta
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from commerce_hub.governance.access import AccessControl, AccessDenied
from commerce_hub.governance.access.tables import grants
from commerce_hub.governance.observability.service import Audit
from commerce_hub.governance.observability.tables import audit_events
from commerce_hub.infrastructure.work import LeaseLost, WorkStore
from commerce_hub.infrastructure.work_tables import work_items
from commerce_hub.orchestration.service import HandlerSpec, TaskError, TaskService
from commerce_hub.orchestration.tables import reports, tasks
from commerce_hub.orchestration.worker import ExecutionContext, Worker
from commerce_hub.scenarios.s01 import S01EngineeringHandler
from tests.support.s01 import example

pytestmark = pytest.mark.mysql


@pytest.fixture
def make_s01(database):
    def make():
        tenant = "s01-" + uuid4().hex
        access = AccessControl(database.engine, "fixture-issuer", "fixture-audience", "fixture-key-" + "x" * 64)
        scope = dict(tenantId=tenant, canonicalSkuIds=["sku-fixture"], storeIds=["store-fixture"],
                     warehouseIds=["warehouse-fixture"], fields=["quantity"])
        with database.engine.begin() as conn:
            now = conn.scalar(select(func.utc_timestamp(6)))
            principal = access.provision_fixture(conn, tenant_id=tenant, principal_id="fixture-actor",
                token_id=uuid4().hex, expires_at=now + timedelta(hours=1),
                grants_by_action={a: scope for a in ["tasks:create", "tasks:read", "tasks:cancel", "engineering:execute"]})
        spec = HandlerSpec("ENGINEERING_S01", "0.1.0", "s01.test." + uuid4().hex, S01EngineeringHandler(),
                           policy_version="engineering-demo-v1")
        queue = WorkStore(database.engine, lease_seconds=30)
        service = TaskService(database.engine, access, queue, Audit(), {spec.scenario_id: spec})
        return SimpleNamespace(database=database, tenant=tenant, principal=principal, scope=scope,
                               access=access, spec=spec, queue=queue, service=service)
    return make


def create(env, value=None, key="fixture-submit"):
    return env.service.create(env.principal, key, env.spec.scenario_id, env.scope, value or example(), uuid4().hex)


def count(env, table, **keys):
    with env.database.engine.connect() as conn:
        return conn.scalar(select(func.count()).select_from(table).filter_by(tenant_id=env.tenant, **keys))


def prepare(env):
    view = create(env)
    lease = env.queue.claim([env.spec.work_kind])
    row = env.service.start(lease, env.principal)
    result = env.spec.handler.run(ExecutionContext(env.service, lease, env.principal, row, Event()), row["parameters"])
    return view["taskRef"]["taskId"], lease, result


def test_pipeline_publishes_one_immutable_report_and_submit_replays(make_s01):
    env = make_s01()
    view = create(env)
    task_id = view["taskRef"]["taskId"]
    with pytest.raises(TaskError, match="REPORT_NOT_PUBLISHED"):
        env.service.read_report(env.principal, task_id)
    assert Worker(env.service).once()
    report = env.service.read_report(env.principal, task_id)
    supply = report["dataReport"]["supplyDemand"]
    assert supply["baseline"]["gapQuantity"] == "15"
    assert supply["candidates"][0]["quantity"] == "20"
    assert report["participants"][0]["snapshotRef"] == report["snapshotRef"]
    replay = create(env)
    assert replay["reportRef"] == report["reportRef"] and replay["state"] == "SUCCEEDED"
    assert count(env, reports) == count(env, tasks) == 1
    # Returned JSON is a copy; historical publication is never overwritten.
    report["dataReport"]["supplyDemand"]["baseline"]["gapQuantity"] = "999"
    assert env.service.read_report(env.principal, task_id)["dataReport"]["supplyDemand"]["baseline"]["gapQuantity"] == "15"
    changed = example()
    changed["inventory"][0]["availableQty"] = "56"
    second = create(env, changed, "changed-sample")
    Worker(env.service).once()
    assert env.service.read_report(env.principal, second["taskRef"]["taskId"])["snapshotRef"] != report["snapshotRef"]


@pytest.mark.parametrize("mode,completeness", [("null", "BLOCKED"), ("constraint", "PARTIAL")])
def test_quality_degradation_is_reported_without_inventing_rules(make_s01, mode, completeness):
    env, value = make_s01(), example()
    if mode == "null":
        value["inventory"][0]["availableQty"] = None
    else:
        value["policy"]["moq"] = None
    task_id = create(env, value)["taskRef"]["taskId"]
    Worker(env.service).once()
    report = env.service.read_report(env.principal, task_id)
    assert report["completeness"] == completeness
    assert report["dataReport"]["supplyDemand"]["candidates"] == []
    assert (report["dataReport"]["supplyDemand"]["baseline"] is None) == (mode == "null")


@pytest.mark.parametrize("failure", ["queue", "audit"])
def test_report_task_audit_and_ack_are_one_transaction(make_s01, monkeypatch, failure):
    env = make_s01()
    task_id, lease, result = prepare(env)
    def fail(*args, **kwargs):
        raise RuntimeError("TEST_OWNED_PUBLICATION_FAILURE")
    with monkeypatch.context() as patch:
        patch.setattr(env.queue if failure == "queue" else env.service.audit,
                      "finish" if failure == "queue" else "record", fail)
        with pytest.raises(RuntimeError, match="TEST_OWNED"):
            env.service.complete(lease, env.principal, 1, result)
    assert count(env, reports) == 0
    assert count(env, audit_events, action="REPORT_PUBLISHED") == 0
    assert env.service.read(env.principal, task_id)["reportRef"] is None
    env.service.complete(lease, env.principal, 1, result)
    with pytest.raises((TaskError, LeaseLost)):
        env.service.complete(lease, env.principal, 1, result)
    assert count(env, reports) == count(env, audit_events, action="REPORT_PUBLISHED") == 1


@pytest.mark.parametrize("fault", ["cancel", "deadline", "lease", "plan", "revoke", "binding", "scope", "missing"])
def test_stale_or_unauthorized_result_never_publishes(make_s01, fault):
    env = make_s01()
    task_id, lease, result = prepare(env)
    with env.database.engine.begin() as conn:
        if fault == "cancel":
            # Use the public cancellation port outside this read-only context.
            pass
        elif fault == "deadline":
            conn.execute(update(tasks).filter_by(tenant_id=env.tenant, task_id=task_id)
                         .values(deadline=conn.scalar(select(func.utc_timestamp(6))) - timedelta(seconds=1)))
        elif fault == "lease":
            conn.execute(update(work_items).filter_by(tenant_id=env.tenant, work_id=lease.work_id)
                         .values(lease_expires=conn.scalar(select(func.utc_timestamp(6))) - timedelta(seconds=1)))
        elif fault == "plan":
            conn.execute(update(tasks).filter_by(tenant_id=env.tenant, task_id=task_id).values(plan_version=2))
        elif fault == "revoke":
            env.access.revoke_token(conn, env.principal)
    if fault == "cancel":
        env.service.cancel(env.principal, task_id, "cancel-fixture", env.service.read(env.principal, task_id)["revision"], "test")
    elif fault == "binding":
        result = result.model_copy(update={"snapshotRef": "broken"})
    elif fault == "scope":
        result = result.model_copy(update={"scope": dict(env.scope, tenantId="other")})
    elif fault == "missing":
        result = None
    with pytest.raises((TaskError, AccessDenied, LeaseLost)):
        env.service.complete(lease, env.principal, 1, result)
    assert count(env, reports) == count(env, audit_events, action="REPORT_PUBLISHED") == 0


def test_report_rechecks_current_scope_and_tenant(make_s01):
    env, other = make_s01(), make_s01()
    task_id = create(env)["taskRef"]["taskId"]
    Worker(env.service).once()
    with pytest.raises(TaskError) as exc:
        other.service.read_report(other.principal, task_id)
    assert exc.value.status == 404
    with env.database.engine.begin() as conn:
        conn.execute(update(grants).filter_by(tenant_id=env.tenant, principal_id=env.principal.principal_id, action="tasks:read")
                     .values(scope=dict(env.scope, canonicalSkuIds=["different-sku"])))
    with pytest.raises(TaskError) as exc:
        env.service.read_report(env.principal, task_id)
    assert exc.value.status == 404


def test_quantity_reader_gets_only_public_view_while_full_assets_remain_internal(make_s01):
    from commerce_hub.data.evidence import resolve
    env = make_s01()
    task_id = create(env)["taskRef"]["taskId"]
    Worker(env.service).once()
    with env.database.engine.begin() as conn:
        raw = conn.execute(select(reports.c.payload).filter_by(tenant_id=env.tenant, task_id=task_id)).scalar_one()
        now = conn.scalar(select(func.utc_timestamp(6)))
        reader = env.access.provision_fixture(conn, tenant_id=env.tenant, principal_id="quantity-reader",
            token_id=uuid4().hex, expires_at=now + timedelta(hours=1),
            grants_by_action={"tasks:read": env.scope})
    assert raw["dataReport"]["inputProjection"]["input"]["mapping"]["sourceSku"] == "fixture-source-sku"
    view = env.service.read_report(reader, task_id)
    assert "inputProjection" not in view["dataReport"] and "manifest" not in view["dataReport"]
    assert "reservedQty" not in str(view) and "sourceSku" not in str(view)
    assert view["dataReport"]["supplyDemand"] == raw["dataReport"]["supplyDemand"]
    raw_evidence = [item for item in raw["dataReport"]["evidence"] if item["fieldPath"].startswith("inputProjection/")]
    assert raw_evidence and all(resolve(view, item["evidenceId"]) is None for item in raw_evidence)
    with env.database.engine.connect() as conn:
        assert conn.execute(select(reports.c.payload).filter_by(tenant_id=env.tenant, task_id=task_id)).scalar_one() == raw


@pytest.mark.parametrize("dimension", ["fields", "canonicalSkuIds", "warehouseIds", "storeIds"])
def test_report_read_rechecks_each_current_scope_dimension(make_s01, dimension):
    env = make_s01()
    task_id = create(env)["taskRef"]["taskId"]
    Worker(env.service).once()
    assert env.service.read_report(env.principal, task_id)["reportRef"]
    with env.database.engine.begin() as conn:
        conn.execute(update(grants).filter_by(tenant_id=env.tenant, principal_id=env.principal.principal_id, action="tasks:read")
            .values(scope=dict(env.scope, **{dimension: ["outside-requested-scope"]})))
    with pytest.raises(TaskError) as exc:
        env.service.read_report(env.principal, task_id)
    assert exc.value.status == 404


@pytest.mark.parametrize("fault", ["missing-read-contract", "wrong-handler-version", "scope-binding"])
def test_report_read_fails_closed_without_matching_read_contract(make_s01, fault):
    env = make_s01()
    task_id = create(env)["taskRef"]["taskId"]
    Worker(env.service).once()
    if fault == "missing-read-contract":
        env.service.registry.clear()
    elif fault == "wrong-handler-version":
        from dataclasses import replace
        env.service.registry[env.spec.scenario_id] = replace(env.spec, version="unsupported")
    else:
        # Corrupt only this test's own asset to verify scope mismatch is not exposed.
        with env.database.engine.begin() as conn:
            raw = conn.execute(select(reports.c.payload).filter_by(tenant_id=env.tenant, task_id=task_id)).scalar_one()
            raw["scope"]["warehouseIds"] = ["outside-requested-scope"]
            conn.execute(update(reports).filter_by(tenant_id=env.tenant, task_id=task_id).values(payload=raw))
    with pytest.raises(TaskError) as exc:
        env.service.read_report(env.principal, task_id)
    assert exc.value.status == 404
