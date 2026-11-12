"""Real MySQL A-05 engineering tests. Unique tenants/kinds; no ERP, model or report fixture."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import os
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from commerce_hub.governance.access import AccessControl, AccessDenied
from commerce_hub.governance.observability.service import Audit
from commerce_hub.governance.observability.tables import audit_events, usage_facts
from commerce_hub.infrastructure.work import LeaseLost, WorkStore
from commerce_hub.infrastructure.work_tables import work_items
from commerce_hub.orchestration.budget import BudgetError, TaskBudgetHandle
from commerce_hub.orchestration.service import HandlerSpec, TaskError, TaskService
from commerce_hub.orchestration.tables import attempts, budgets, commands, tasks
from commerce_hub.orchestration.worker import RetryableStep, Worker

pytestmark = [pytest.mark.mysql, pytest.mark.skipif(os.environ.get("COMMERCE_RUN_MYSQL_TESTS") != "1",
                                                  reason="Real MySQL engineering tests are opt-in")]


class FixtureHandler:
    def __init__(self, callback=None):
        self.calls = 0
        self.callback = callback

    def validate(self, parameters):
        if not isinstance(parameters, dict) or set(parameters) != {"mode"} or parameters["mode"] not in {"ok", "retry"}:
            raise TaskError("INVALID_ENGINEERING_FIXTURE", 422)

    def run(self, context, parameters):
        self.calls += 1
        context.check()
        if self.callback:
            self.callback(context)
        if parameters["mode"] == "retry":
            raise RetryableStep("fixture-controlled-retry")


class FailingAudit(Audit):
    def __init__(self, action):
        self.action = action

    def record(self, connection, **values):
        ref = super().record(connection, **values)
        if values["action"] == self.action:
            raise RuntimeError("FIXTURE_AUDIT_FAILURE")
        return ref


@pytest.fixture
def make_foundation(database):
    def make(*, max_calls=2, max_tokens=100, max_cost=Decimal("1"), max_attempts=3,
             deadline_seconds=120, audit=None, callback=None):
        tenant = "orchestration-" + uuid4().hex
        kind = "o01.engineering." + uuid4().hex
        access = AccessControl(database.engine, "fixture-issuer", "fixture-audience", "fixture-only-key-" + "x" * 64)
        scope = {"tenantId": tenant, "storeIds": ["store-fixture"], "warehouseIds": ["warehouse-fixture"],
                 "canonicalSkuIds": ["sku-fixture"], "fields": ["status"]}
        with database.engine.begin() as connection:
            now = connection.scalar(select(func.utc_timestamp(6)))
            principal = access.provision_fixture(connection, tenant_id=tenant, principal_id="actor-fixture",
                token_id=uuid4().hex, expires_at=now + timedelta(hours=1),
                grants_by_action={action: scope for action in ["tasks:create", "tasks:read", "tasks:cancel", "engineering:execute"]})
        handler = FixtureHandler(callback)
        queue = WorkStore(database.engine, lease_seconds=30)
        spec = HandlerSpec("ENGINEERING_FIXTURE", "1", kind, handler, max_calls=max_calls,
                           max_tokens=max_tokens, max_cost=max_cost, policy_version="fixture-budget-v1")
        service = TaskService(database.engine, access, queue, audit or Audit(), {spec.scenario_id: spec},
                              deadline_seconds=deadline_seconds, max_attempts=max_attempts)
        return SimpleNamespace(database=database, tenant=tenant, principal=principal, scope=scope,
                               access=access, queue=queue, service=service, handler=handler, kind=kind)
    return make


def create(env, key="create-fixture", mode="ok"):
    return env.service.create(env.principal, key, "ENGINEERING_FIXTURE", env.scope, {"mode": mode}, uuid4().hex)


def owned_row(env, table, **keys):
    with env.database.engine.connect() as connection:
        return connection.execute(select(table).filter_by(tenant_id=env.tenant, **keys)).mappings().one()


def count(env, table, **keys):
    with env.database.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table).filter_by(tenant_id=env.tenant, **keys))


def running(env):
    view = create(env)
    lease = env.queue.claim([env.kind])
    assert lease is not None and lease.tenant_id == env.tenant
    env.service.start(lease, env.principal)
    return view, lease, TaskBudgetHandle(env.service, lease, env.principal, 1)


def accounting_snapshot(env):
    with env.database.engine.connect() as connection:
        return {table.name: [dict(row) for row in connection.execute(select(table)
            .filter_by(tenant_id=env.tenant).order_by(*table.primary_key.columns)).mappings()]
            for table in [budgets, attempts, usage_facts, audit_events]}


def expire_owned_lease(env, lease):
    with env.database.engine.begin() as connection:
        now = connection.scalar(select(func.utc_timestamp(6)))
        connection.execute(update(work_items).where(work_items.c.tenant_id == env.tenant,
                           work_items.c.work_id == lease.work_id)
                           .values(lease_expires=now - timedelta(seconds=1)))


def test_create_rolls_back_task_work_budget_and_required_audit(make_foundation):
    env = make_foundation(audit=FailingAudit("TASK_CREATED"))
    with pytest.raises(RuntimeError, match="FIXTURE_AUDIT_FAILURE"):
        create(env)
    for table in [tasks, work_items, budgets, audit_events]:
        assert count(env, table) == 0


def test_same_command_replays_one_persisted_task_and_work(make_foundation):
    env = make_foundation()
    first, second = create(env), create(env)
    assert first == second
    assert first["sourceNature"] == "SIMULATED_ENGINEERING" and first["reportRef"] is None
    for table in [tasks, work_items, budgets, audit_events]:
        assert count(env, table) == 1


def test_same_command_with_changed_content_conflicts(make_foundation):
    env = make_foundation()
    create(env)
    with pytest.raises(TaskError, match="COMMAND_CONFLICT"):
        create(env, mode="retry")
    assert count(env, tasks) == count(env, work_items) == 1


def test_same_key_and_sku_in_other_tenant_does_not_reuse_task(make_foundation):
    first, second = make_foundation(), make_foundation()
    left, right = create(first), create(second)
    assert left["taskRef"] != right["taskRef"]
    with pytest.raises(TaskError) as error:
        first.service.read(first.principal, right["taskRef"]["taskId"])
    assert error.value.status == 404


def test_two_concurrent_create_commands_are_idempotent(make_foundation):
    env = make_foundation()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(env), range(2)))
    assert results[0]["taskRef"] == results[1]["taskRef"]
    assert count(env, tasks) == count(env, work_items) == count(env, audit_events) == 1


def test_invalid_fixture_and_unregistered_s01_are_rejected_before_admission(make_foundation):
    env = make_foundation()
    with pytest.raises(TaskError, match="INVALID_ENGINEERING_FIXTURE"):
        env.service.create(env.principal, "fixture", "ENGINEERING_FIXTURE", env.scope, {"unsafe": True}, uuid4().hex)
    with pytest.raises(TaskError, match="UNSUPPORTED_SCENARIO"):
        env.service.create(env.principal, "fixture", "S01", env.scope, {}, uuid4().hex)
    assert count(env, tasks) == count(env, work_items) == 0


def test_two_workers_only_one_claims_single_delivery(make_foundation):
    env = make_foundation()
    create(env)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: env.queue.claim([env.kind]), range(2)))
    assert sum(lease is not None for lease in claims) == 1
    assert owned_row(env, work_items)["attempt"] == 1
    assert env.queue.claim(["unknown-fixture-kind"]) is None


def test_complete_requires_current_lease_and_plan(make_foundation):
    env = make_foundation()
    view, lease, _ = running(env)
    with pytest.raises(LeaseLost):
        env.service.complete(replace(lease, token=uuid4().hex), env.principal, 1)
    with pytest.raises(TaskError, match="STALE_PLAN"):
        env.service.complete(lease, env.principal, 2)
    assert owned_row(env, tasks)["state"] == "RUNNING"
    env.service.complete(lease, env.principal, 1)
    assert env.service.read(env.principal, view["taskRef"]["taskId"])["state"] == "SUCCEEDED"
    assert owned_row(env, work_items)["state"] == "DONE"
    assert count(env, audit_events, action="TASK_COMPLETED") == 1


def test_lost_lease_recovers_same_task_without_resetting_deadline_or_budget(make_foundation):
    env = make_foundation(max_calls=1)
    view, lease, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    before = owned_row(env, tasks)
    expire_owned_lease(env, lease)
    with pytest.raises(LeaseLost):
        env.queue.heartbeat(lease)
    env.queue.recover_expired([env.kind])
    replacement = env.queue.claim([env.kind])
    assert replacement.owner_id == lease.owner_id and replacement.attempt == 2 and replacement.token != lease.token
    env.service.start(replacement, env.principal)
    with pytest.raises(LeaseLost):
        env.service.checkpoint(lease, env.principal, 1)
    current_budget = TaskBudgetHandle(env.service, replacement, env.principal, 1)
    with pytest.raises(BudgetError, match="BUDGET_DENIED"):
        current_budget.reserve("another", "another", 1, "0.01")
    assert owned_row(env, tasks)["deadline"] == before["deadline"]
    assert env.service.read(env.principal, view["taskRef"]["taskId"])["taskRef"] == view["taskRef"]
    env.service.complete(replacement, env.principal, 1)


def test_exhausted_delivery_reconciles_owner_once(make_foundation):
    env = make_foundation(max_attempts=1)
    _, lease, _ = running(env)
    expire_owned_lease(env, lease)
    env.queue.recover_expired([env.kind])
    env.service.reconcile_dead()
    env.service.reconcile_dead()
    assert owned_row(env, work_items)["state"] == "DEAD"
    assert owned_row(env, tasks)["error_code"] == "DELIVERY_EXHAUSTED"
    assert count(env, audit_events, action="TASK_FAILED") == 1
    assert env.queue.claim([env.kind]) is None


def test_cancel_queued_is_idempotent_and_does_not_publish(make_foundation):
    env = make_foundation()
    view = create(env)
    task_id = view["taskRef"]["taskId"]
    first = env.service.cancel(env.principal, task_id, "cancel-fixture", 1, uuid4().hex)
    second = env.service.cancel(env.principal, task_id, "cancel-fixture", 1, uuid4().hex)
    assert first == second and first["state"] == "CANCELLED" and first["reportRef"] is None
    assert owned_row(env, work_items)["state"] == "CANCELLED"
    assert count(env, audit_events, action="TASK_CANCELLED") == 1
    assert env.queue.claim([env.kind]) is None
    with pytest.raises(TaskError, match="COMMAND_CONFLICT"):
        env.service.cancel(env.principal, task_id, "cancel-fixture", 2, uuid4().hex)


def test_cancel_running_rejects_late_completion(make_foundation):
    env = make_foundation()
    view, lease, _ = running(env)
    current = env.service.read(env.principal, view["taskRef"]["taskId"])
    env.service.cancel(env.principal, view["taskRef"]["taskId"], "cancel-fixture", current["revision"], uuid4().hex)
    with pytest.raises(LeaseLost):
        env.service.complete(lease, env.principal, 1)
    assert owned_row(env, tasks)["state"] == "CANCELLED"
    assert count(env, audit_events, action="TASK_COMPLETED") == 0


def test_worker_deadline_expiry_is_bounded_failure(make_foundation):
    env = make_foundation(deadline_seconds=-1)
    create(env)
    assert Worker(env.service).once()
    assert owned_row(env, tasks)["state"] == "FAILED"
    assert owned_row(env, tasks)["error_code"] == "DEADLINE_EXCEEDED"
    assert owned_row(env, work_items)["state"] == "DEAD"
    assert not Worker(env.service).once()


def test_worker_rechecks_revoked_actor_before_handler(make_foundation):
    env = make_foundation()
    create(env)
    with env.database.engine.begin() as connection:
        env.access.revoke_principal(connection, env.principal)
    assert Worker(env.service).once()
    assert env.handler.calls == 0
    assert owned_row(env, tasks)["error_code"] == "POLICY_DENIED"
    assert owned_row(env, work_items)["state"] == "DEAD"


def test_completion_audit_failure_rolls_back_owner_and_delivery(make_foundation):
    env = make_foundation()
    _, lease, _ = running(env)
    env.service.audit = FailingAudit("TASK_COMPLETED")
    with pytest.raises(RuntimeError, match="FIXTURE_AUDIT_FAILURE"):
        env.service.complete(lease, env.principal, 1)
    assert owned_row(env, tasks)["state"] == "RUNNING"
    assert owned_row(env, work_items)["state"] == "LEASED"
    assert count(env, audit_events, action="TASK_COMPLETED") == 0
    env.service.audit = Audit()
    env.service.complete(lease, env.principal, 1)
    assert owned_row(env, tasks)["state"] == "SUCCEEDED"


def test_budget_two_threads_cannot_overreserve_original_task(make_foundation):
    env = make_foundation(max_calls=1, max_tokens=10, max_cost=Decimal("0.1"))
    _, _, budget = running(env)
    def reserve(index):
        try:
            return budget.reserve("fixture-call-" + str(index), "attempt-" + str(index), 10, "0.1")
        except BudgetError as error:
            return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, range(2)))
    assert sum(isinstance(result, dict) for result in results) == 1
    assert results.count("BUDGET_DENIED") == 1
    row = owned_row(env, budgets)
    assert row["reserved_calls"] == 1 and row["reserved_tokens"] == 10 and row["reserved_cost"] == Decimal("0.1")


def test_attempt_reservation_replay_and_content_conflict(make_foundation):
    env = make_foundation()
    _, _, budget = running(env)
    first = budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    assert budget.reserve("fixture-call", "fixture-attempt", 10, "0.1") == first
    with pytest.raises(BudgetError, match="ATTEMPT_CONFLICT"):
        budget.reserve("fixture-call", "fixture-attempt", 11, "0.1")
    assert count(env, attempts) == 1 and owned_row(env, budgets)["reserved_calls"] == 1


def test_unknown_usage_stays_reserved_and_cannot_be_resent_or_refunded(make_foundation):
    env = make_foundation(max_calls=1)
    _, _, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    budget.mark_sent("fixture-attempt")
    budget.unknown("fixture-attempt")
    assert budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")["state"] == "UNKNOWN"
    with pytest.raises(BudgetError, match="USAGE_MUST_BE_RECONCILED"):
        budget.release_unsent("fixture-attempt")
    with pytest.raises(BudgetError, match="ATTEMPT_NOT_SENDABLE"):
        budget.mark_sent("fixture-attempt")
    with pytest.raises(BudgetError, match="BUDGET_DENIED"):
        budget.reserve("other-call", "other-attempt", 1, "0.01")
    assert owned_row(env, budgets)["reserved_calls"] == 1
    assert owned_row(env, attempts)["state"] == "UNKNOWN"
    assert count(env, usage_facts) == 0


def test_old_plan_failure_cannot_change_new_plan_state(make_foundation):
    env = make_foundation()
    _, lease, _ = running(env)
    with env.database.engine.begin() as conn:
        conn.execute(update(tasks).filter_by(tenant_id=env.tenant, task_id=lease.owner_id).values(plan_version=2))
    env.service.fail(lease, "STALE_PLAN", plan_version=1)
    assert owned_row(env, tasks)["state"] == "RUNNING"
    assert owned_row(env, tasks)["plan_version"] == 2


def test_explicit_new_owner_version_can_start_without_old_delivery_rebinding(make_foundation):
    env = make_foundation()
    view = create(env)
    with env.database.engine.begin() as conn:
        conn.execute(update(tasks).filter_by(tenant_id=env.tenant).values(plan_version=2))
        conn.execute(update(work_items).filter_by(tenant_id=env.tenant).values(owner_version=2))
    lease = env.queue.claim([env.kind])
    assert lease.owner_version == 2
    context = env.service.start(lease, env.principal)
    assert context["plan_version"] == 2
    env.service.complete(lease, env.principal, 2)
    assert env.service.read(env.principal, view["taskRef"]["taskId"])["state"] == "SUCCEEDED"


def test_lease_cannot_be_rebound_to_another_owner_or_work_kind(make_foundation):
    env = make_foundation()
    _, lease, _ = running(env)
    for forged in [replace(lease, owner_id=uuid4().hex), replace(lease, kind="unregistered-kind"),
                   replace(lease, attempt=lease.attempt + 1), replace(lease, owner_version=2)]:
        with env.database.engine.begin() as conn:
            with pytest.raises(LeaseLost):
                env.queue.validate(conn, forged)


def test_unknown_logical_call_cannot_retry_under_a_new_attempt(make_foundation):
    env = make_foundation(max_calls=3)
    _, _, budget = running(env)
    budget.reserve("same-logical-call", "first-attempt", 10, "0.1")
    budget.mark_sent("first-attempt")
    budget.unknown("first-attempt")
    with pytest.raises(BudgetError, match="USAGE_MUST_BE_RECONCILED"):
        budget.reserve("same-logical-call", "replacement-attempt", 10, "0.1")
    assert count(env, attempts) == 1
    assert owned_row(env, budgets)["reserved_calls"] == 1


@pytest.mark.parametrize("state,code", [("RESERVED", "ATTEMPT_NOT_SETTLEABLE"), ("RELEASED", "ATTEMPT_RELEASED")])
@pytest.mark.parametrize("cancelled", [False, True])
def test_unsent_usage_settlement_leaves_all_accounting_facts_unchanged(make_foundation, state, code, cancelled):
    env = make_foundation()
    view, _, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    if state == "RELEASED":
        budget.release_unsent("fixture-attempt")
    if cancelled:
        current = env.service.read(env.principal, view["taskRef"]["taskId"])
        env.service.cancel(env.principal, view["taskRef"]["taskId"], "cancel-fixture", current["revision"], uuid4().hex)
    before = accounting_snapshot(env)
    assert owned_row(env, attempts)["state"] == state
    with pytest.raises(BudgetError, match="^" + code + "$"):
        budget.settle("fixture-attempt", 7, "0.07")
    assert accounting_snapshot(env) == before
    assert count(env, usage_facts) == 0
    assert count(env, audit_events, action="USAGE_SETTLED") == 0


@pytest.mark.parametrize("state", ["SENT", "UNKNOWN"])
@pytest.mark.parametrize("over_limit", [False, True])
def test_sent_usage_settlement_replay_checks_every_usage_dimension(make_foundation, state, over_limit):
    env = make_foundation()
    _, _, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    budget.mark_sent("fixture-attempt")
    if state == "UNKNOWN":
        budget.unknown("fixture-attempt")
    cost = "0.2" if over_limit else "0.07"
    usage = dict(tokens=7, cost=cost, currency="TEST", pricing_version="fixture-v1")
    ref = budget.settle("fixture-attempt", **usage)
    assert owned_row(env, attempts)["state"] == ("SETTLED_OVER_LIMIT" if over_limit else "SETTLED")
    row = owned_row(env, budgets)
    assert (row["reserved_calls"], row["reserved_tokens"], row["reserved_cost"]) == (0, 0, Decimal("0"))
    assert (row["used_calls"], row["used_tokens"], row["used_cost"]) == (1, 7, Decimal(cost))
    assert count(env, usage_facts) == count(env, audit_events, action="USAGE_SETTLED") == 1
    before = accounting_snapshot(env)
    assert budget.settle("fixture-attempt", **usage) == ref
    assert accounting_snapshot(env) == before
    for patch in [dict(tokens=8), dict(cost="0.08"), dict(currency="USD"), dict(pricing_version="fixture-v2")]:
        with pytest.raises(ValueError, match="^USAGE_CONFLICT$"):
            budget.settle("fixture-attempt", **(usage | patch))
        assert accounting_snapshot(env) == before


def test_usage_settlement_is_idempotent_and_g02_is_unique_fact(make_foundation):
    env = make_foundation()
    _, _, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    budget.mark_sent("fixture-attempt")
    ref = budget.settle("fixture-attempt", 7, "0.07")
    assert budget.settle("fixture-attempt", 7, "0.07") == ref
    assert count(env, usage_facts) == 1
    assert count(env, audit_events, action="USAGE_SETTLED") == 1
    row = owned_row(env, budgets)
    assert row["used_calls"] == 1 and row["reserved_calls"] == 0 and row["used_cost"] == Decimal("0.07")
    with pytest.raises(ValueError, match="USAGE_CONFLICT"):
        budget.settle("fixture-attempt", 8, "0.07")


def test_actual_over_limit_usage_is_not_clamped_and_blocks_more_calls(make_foundation):
    env = make_foundation(max_calls=2, max_tokens=10, max_cost=Decimal("1"))
    _, _, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 5, "0.5")
    budget.mark_sent("fixture-attempt")
    budget.settle("fixture-attempt", 7, "2")
    assert owned_row(env, attempts)["state"] == "SETTLED_OVER_LIMIT"
    assert owned_row(env, budgets)["used_cost"] == Decimal("2")
    assert owned_row(env, usage_facts)["cost"] == Decimal("2")
    with pytest.raises(BudgetError, match="BUDGET_DENIED"):
        budget.reserve("next-call", "next-attempt", 1, "0.01")


def test_unsent_release_is_idempotent_and_never_refunds_spent_usage(make_foundation):
    env = make_foundation(max_calls=1)
    _, _, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    budget.release_unsent("fixture-attempt")
    budget.release_unsent("fixture-attempt")
    assert owned_row(env, budgets)["reserved_calls"] == 0
    budget.reserve("next-call", "next-attempt", 10, "0.1")
    budget.mark_sent("next-attempt")
    with pytest.raises(BudgetError, match="USAGE_MUST_BE_RECONCILED"):
        budget.release_unsent("next-attempt")


def test_settlement_required_audit_failure_rolls_back_usage_and_control(make_foundation):
    env = make_foundation()
    _, _, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    budget.mark_sent("fixture-attempt")
    env.service.audit = FailingAudit("USAGE_SETTLED")
    with pytest.raises(RuntimeError, match="FIXTURE_AUDIT_FAILURE"):
        budget.settle("fixture-attempt", 7, "0.07")
    assert count(env, usage_facts) == 0
    assert owned_row(env, attempts)["state"] == "SENT"
    assert owned_row(env, budgets)["reserved_calls"] == 1 and owned_row(env, budgets)["used_calls"] == 0
    env.service.audit = Audit()
    budget.settle("fixture-attempt", 7, "0.07")
    assert count(env, usage_facts) == 1


def test_worker_retry_is_bounded_and_keeps_original_deadline(make_foundation):
    env = make_foundation(max_attempts=2)
    create(env, mode="retry")
    deadline = owned_row(env, tasks)["deadline"]
    worker = Worker(env.service)
    assert worker.once()
    assert owned_row(env, tasks)["state"] == "QUEUED" and owned_row(env, work_items)["state"] == "RETRY_WAIT"
    time.sleep(0.15)
    assert worker.once()
    assert owned_row(env, tasks)["state"] == "FAILED" and owned_row(env, work_items)["attempt"] == 2
    assert owned_row(env, tasks)["deadline"] == deadline
    assert env.handler.calls == 2 and not worker.once()


def test_handler_runs_outside_owner_transaction_and_emits_no_report(make_foundation):
    def callback(context):
        with context.service.engine.begin() as connection:
            row = connection.execute(select(tasks.c.state).where(tasks.c.tenant_id == context.lease.tenant_id,
                tasks.c.task_id == context.lease.owner_id).with_for_update(nowait=True)).scalar_one()
            assert row == "RUNNING"
    env = make_foundation(callback=callback)
    view = create(env)
    assert Worker(env.service).once()
    result = env.service.read(env.principal, view["taskRef"]["taskId"])
    assert result["state"] == "SUCCEEDED" and result["reportRef"] is None


def test_cancel_required_audit_failure_rolls_back_task_command_and_work(make_foundation):
    env = make_foundation()
    view, lease, _ = running(env)
    before = env.service.read(env.principal, view["taskRef"]["taskId"])
    env.service.audit = FailingAudit("TASK_CANCELLED")
    with pytest.raises(RuntimeError, match="FIXTURE_AUDIT_FAILURE"):
        env.service.cancel(env.principal, view["taskRef"]["taskId"], "cancel-fixture", before["revision"], uuid4().hex)
    assert owned_row(env, tasks)["state"] == "RUNNING"
    assert owned_row(env, tasks)["revision"] == before["revision"]
    assert owned_row(env, work_items)["state"] == "LEASED"
    assert count(env, commands) == count(env, audit_events, action="TASK_CANCELLED") == 0
    env.service.audit = Audit()
    env.service.complete(lease, env.principal, 1)


def test_only_one_concurrent_sender_can_mark_attempt_sent(make_foundation):
    env = make_foundation()
    _, _, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    def send_boundary(_):
        try:
            budget.mark_sent("fixture-attempt")
            return "SENT"
        except BudgetError as error:
            return str(error)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send_boundary, range(2)))
    assert sorted(results) == ["ATTEMPT_NOT_SENDABLE", "SENT"]
    assert owned_row(env, attempts)["state"] == "SENT"


def test_late_unknown_usage_is_accounted_after_cancel_without_reopening_task(make_foundation):
    env = make_foundation()
    view, lease, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    budget.mark_sent("fixture-attempt")
    budget.unknown("fixture-attempt")
    current = env.service.read(env.principal, view["taskRef"]["taskId"])
    env.service.cancel(env.principal, view["taskRef"]["taskId"], "cancel-fixture", current["revision"], uuid4().hex)
    ref = budget.settle("fixture-attempt", 7, "0.07")
    assert ref and owned_row(env, tasks)["state"] == "CANCELLED"
    assert owned_row(env, work_items)["state"] == "CANCELLED"
    assert owned_row(env, budgets)["used_calls"] == 1
    with pytest.raises(LeaseLost):
        budget.reserve("another", "another", 1, "0.01")


def test_late_sent_usage_is_accounted_and_replayed_after_cancel(make_foundation):
    env = make_foundation()
    view, _, budget = running(env)
    budget.reserve("fixture-call", "fixture-attempt", 10, "0.1")
    budget.mark_sent("fixture-attempt")
    current = env.service.read(env.principal, view["taskRef"]["taskId"])
    env.service.cancel(env.principal, view["taskRef"]["taskId"], "cancel-fixture", current["revision"], uuid4().hex)
    ref = budget.settle("fixture-attempt", 7, "0.07")
    before = accounting_snapshot(env)
    assert budget.settle("fixture-attempt", 7, "0.07") == ref
    assert accounting_snapshot(env) == before
    assert owned_row(env, tasks)["state"] == owned_row(env, work_items)["state"] == "CANCELLED"
    assert owned_row(env, attempts)["state"] == "SETTLED"
    assert owned_row(env, usage_facts)["usage_ref"] == ref
    assert owned_row(env, budgets)["used_calls"] == 1
