"""Real isolated-MySQL coverage for additive optional model usage facts."""
from datetime import timedelta
from decimal import Decimal
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from commerce_hub.governance.access import AccessControl
from commerce_hub.governance.observability.service import Audit
from commerce_hub.governance.observability.tables import audit_events, usage_facts
from commerce_hub.infrastructure.work import WorkStore
from commerce_hub.infrastructure.work_tables import work_items
from commerce_hub.orchestration.budget import TaskBudgetHandle
from commerce_hub.orchestration.service import HandlerSpec, TaskService
from commerce_hub.orchestration.tables import attempts, budgets, reports, tasks


pytestmark = [
    pytest.mark.mysql,
    pytest.mark.skipif(
        os.environ.get("COMMERCE_RUN_MYSQL_TESTS") != "1",
        reason="Real MySQL optional-usage tests are opt-in",
    ),
]


class UsageHandler:
    def validate(self, parameters):
        if parameters != {"mode": "usage"}:
            raise ValueError("INVALID_USAGE_FIXTURE")

    def run(self, context, parameters):
        context.check()


class FailingUsageFactAudit(Audit):
    def record_usage(self, connection, **values):
        super().record_usage(connection, **values)
        raise RuntimeError("FIXTURE_G02_FAILURE")


class FailingRequiredAudit(Audit):
    def record(self, connection, **values):
        ref = super().record(connection, **values)
        if values["action"] in {"USAGE_RECORDED", "USAGE_SETTLED"}:
            raise RuntimeError("FIXTURE_AUDIT_FAILURE")
        return ref


@pytest.fixture
def usage_env(database):
    tenant = "optional-usage-" + uuid4().hex
    kind = "o01.optional-usage." + uuid4().hex
    access = AccessControl(
        database.engine,
        "fixture-issuer",
        "fixture-audience",
        "fixture-only-key-" + "x" * 64,
    )
    scope = {
        "tenantId": tenant,
        "storeIds": ["store-fixture"],
        "warehouseIds": ["warehouse-fixture"],
        "canonicalSkuIds": ["sku-fixture"],
        "fields": ["status"],
    }
    with database.engine.begin() as connection:
        now = connection.scalar(select(func.utc_timestamp(6)))
        principal = access.provision_fixture(
            connection,
            tenant_id=tenant,
            principal_id="actor-fixture",
            token_id=uuid4().hex,
            expires_at=now + timedelta(hours=1),
            grants_by_action={
                action: scope
                for action in ["tasks:create", "tasks:read", "tasks:cancel", "engineering:execute"]
            },
        )
    queue = WorkStore(database.engine, lease_seconds=30)
    spec = HandlerSpec(
        "OPTIONAL_USAGE_FIXTURE",
        "1",
        kind,
        UsageHandler(),
        max_calls=3,
        max_tokens=300,
        max_cost=Decimal("3"),
        policy_version="optional-usage-v1",
    )
    service = TaskService(database.engine, access, queue, Audit(), {spec.scenario_id: spec})
    view = service.create(
        principal,
        "create-" + uuid4().hex,
        spec.scenario_id,
        scope,
        {"mode": "usage"},
        uuid4().hex,
    )
    lease = queue.claim([kind])
    assert lease is not None and lease.tenant_id == tenant
    service.start(lease, principal)
    return SimpleNamespace(
        database=database,
        tenant=tenant,
        principal=principal,
        queue=queue,
        service=service,
        view=view,
        lease=lease,
        budget=TaskBudgetHandle(service, lease, principal, 1),
    )


def row(env, table, **keys):
    with env.database.engine.connect() as connection:
        return connection.execute(
            select(table).filter_by(tenant_id=env.tenant, **keys)
        ).mappings().one()


def count(env, table, **keys):
    with env.database.engine.connect() as connection:
        return connection.scalar(
            select(func.count()).select_from(table).filter_by(tenant_id=env.tenant, **keys)
        )


def snapshot(env):
    with env.database.engine.connect() as connection:
        return {
            table.name: [
                dict(item)
                for item in connection.execute(
                    select(table)
                    .filter_by(tenant_id=env.tenant)
                    .order_by(*table.primary_key.columns)
                ).mappings()
            ]
            for table in [budgets, attempts, usage_facts, audit_events, tasks, work_items, reports]
        }


def sent_attempt(env, *, attempt_id="attempt-1", logical_call_id="call-1", tokens=100, cost="0.5"):
    env.budget.reserve(logical_call_id, attempt_id, tokens, cost)
    env.budget.mark_sent(attempt_id)
    return attempt_id


def test_currency_cannot_be_mixed_between_attempts(usage_env):
    env = usage_env
    sent_attempt(env)
    env.budget.settle("attempt-1", 30, "0.1", currency="USD")
    sent_attempt(env, attempt_id="attempt-2", logical_call_id="call-2")
    before = snapshot(env)
    with pytest.raises(ValueError, match="USAGE_CURRENCY_CONFLICT"):
        env.budget.settle("attempt-2", 30, "0.1", currency="CNY")
    assert snapshot(env) == before


def test_cache_only_lower_bound_and_later_dimensions_cannot_hide_overrun(usage_env):
    env = usage_env
    sent_attempt(env)
    env.budget.record_model_usage("attempt-1", cached_input_tokens=60)
    env.budget.record_model_usage("attempt-1", uncached_input_tokens=60)
    assert row(env, attempts, attempt_id="attempt-1")["state"] == "USAGE_OVER_LIMIT"
    assert row(env, budgets)["reserved_tokens"] == 100
    with pytest.raises(ValueError, match="USAGE_CONFLICT"):
        env.budget.record_model_usage("attempt-1", total_tokens=100)
    env.budget.record_model_usage("attempt-1", input_tokens=120, output_tokens=1)
    assert row(env, usage_facts, attempt_id="attempt-1")["tokens"] == 121
    assert row(env, attempts, attempt_id="attempt-1")["state"] == "USAGE_OVER_LIMIT"


def test_known_token_dimensions_unknown_cost_persist_and_later_cost_moves_reservation_once(usage_env):
    env = usage_env
    attempt_id = sent_attempt(env)
    usage = dict(
        total_tokens=30,
        input_tokens=10,
        output_tokens=20,
        cached_input_tokens=4,
        uncached_input_tokens=6,
        currency="USD",
        pricing_version="deepseek-contract-v1",
    )
    ref = env.budget.record_model_usage(attempt_id, **usage)

    fact = row(env, usage_facts, task_id=env.lease.owner_id, attempt_id=attempt_id)
    assert (fact["tokens"], fact["input_tokens"], fact["output_tokens"]) == (30, 10, 20)
    assert (fact["cached_input_tokens"], fact["uncached_input_tokens"], fact["cost"]) == (4, 6, None)
    assert (fact["currency"], fact["pricing_version"], fact["usage_ref"]) == (
        "USD", "deepseek-contract-v1", ref)
    control = row(env, budgets, task_id=env.lease.owner_id)
    assert (control["used_calls"], control["reserved_calls"]) == (1, 0)
    assert (control["used_tokens"], control["reserved_tokens"]) == (30, 0)
    assert (control["used_cost"], control["reserved_cost"]) == (Decimal("0"), Decimal("0.5"))
    assert row(env, attempts, task_id=env.lease.owner_id, attempt_id=attempt_id)["state"] == "USAGE_RECORDED"

    before_replay = snapshot(env)
    assert env.budget.record_model_usage(attempt_id, **usage) == ref
    assert snapshot(env) == before_replay
    with pytest.raises(ValueError, match="^USAGE_CONFLICT$"):
        env.budget.record_model_usage(attempt_id, **(usage | {"output_tokens": 21, "total_tokens": 31}))
    assert snapshot(env) == before_replay

    assert env.budget.record_model_usage(
        attempt_id,
        cost="0.03",
        currency="USD",
        pricing_version="deepseek-contract-v1",
    ) == ref
    settled = snapshot(env)
    control = row(env, budgets, task_id=env.lease.owner_id)
    assert (control["used_cost"], control["reserved_cost"]) == (Decimal("0.03"), Decimal("0"))
    assert row(env, attempts, task_id=env.lease.owner_id, attempt_id=attempt_id)["state"] == "SETTLED"
    assert count(env, audit_events, task_id=env.lease.owner_id, action="USAGE_RECORDED") == 1
    assert count(env, audit_events, task_id=env.lease.owner_id, action="USAGE_SETTLED") == 1
    assert env.budget.record_model_usage(
        attempt_id,
        cost="0.03",
        currency="USD",
        pricing_version="deepseek-contract-v1",
    ) == ref
    assert snapshot(env) == settled


def test_partial_token_fact_keeps_token_reservation_until_total_becomes_known(usage_env):
    env = usage_env
    attempt_id = sent_attempt(env)
    ref = env.budget.record_model_usage(
        attempt_id,
        input_tokens=10,
        cached_input_tokens=4,
        uncached_input_tokens=6,
        cost="0.03",
        currency="USD",
        pricing_version="deepseek-contract-v1",
    )
    fact = row(env, usage_facts, task_id=env.lease.owner_id, attempt_id=attempt_id)
    assert fact["tokens"] is None and fact["input_tokens"] == 10 and fact["output_tokens"] is None
    control = row(env, budgets, task_id=env.lease.owner_id)
    assert (control["used_tokens"], control["reserved_tokens"]) == (0, 100)
    assert (control["used_cost"], control["reserved_cost"]) == (Decimal("0.03"), Decimal("0"))
    assert row(env, attempts, task_id=env.lease.owner_id, attempt_id=attempt_id)["state"] == "USAGE_RECORDED"

    assert env.budget.record_model_usage(
        attempt_id,
        total_tokens=30,
        output_tokens=20,
        currency="USD",
        pricing_version="deepseek-contract-v1",
    ) == ref
    control = row(env, budgets, task_id=env.lease.owner_id)
    assert (control["used_tokens"], control["reserved_tokens"]) == (30, 0)
    assert (control["used_cost"], control["reserved_cost"]) == (Decimal("0.03"), Decimal("0"))
    assert row(env, attempts, task_id=env.lease.owner_id, attempt_id=attempt_id)["state"] == "SETTLED"


def test_late_usage_after_cancel_accounts_without_task_or_report_publication(usage_env):
    env = usage_env
    attempt_id = sent_attempt(env)
    env.budget.unknown(attempt_id)
    task_id = env.lease.owner_id
    current = env.service.read(env.principal, task_id)
    env.service.cancel(env.principal, task_id, "cancel-" + uuid4().hex, current["revision"], uuid4().hex)

    ref = env.budget.record_model_usage(
        attempt_id,
        total_tokens=30,
        input_tokens=10,
        output_tokens=20,
        cost="0.03",
        currency="USD",
        pricing_version="deepseek-contract-v1",
    )
    assert ref
    assert row(env, tasks, task_id=task_id)["state"] == "CANCELLED"
    assert row(env, work_items, owner_id=task_id)["state"] == "CANCELLED"
    assert count(env, reports, task_id=task_id) == 0
    assert count(env, audit_events, task_id=task_id, action="TASK_COMPLETED") == 0
    assert row(env, budgets, task_id=task_id)["used_calls"] == 1
    assert row(env, attempts, task_id=task_id, attempt_id=attempt_id)["state"] == "SETTLED"


def test_legacy_complete_settle_remains_compatible_with_optional_dimensions(usage_env):
    env = usage_env
    attempt_id = sent_attempt(env)
    ref = env.budget.settle(
        attempt_id,
        30,
        "0.03",
        currency="USD",
        pricing_version="deepseek-contract-v1",
        input_tokens=10,
        output_tokens=20,
        cached_input_tokens=4,
        uncached_input_tokens=6,
    )
    fact = row(env, usage_facts, task_id=env.lease.owner_id, attempt_id=attempt_id)
    assert fact["usage_ref"] == ref
    assert (fact["tokens"], fact["input_tokens"], fact["output_tokens"]) == (30, 10, 20)
    assert (fact["cached_input_tokens"], fact["uncached_input_tokens"]) == (4, 6)
    assert fact["cost"] == Decimal("0.03")
    assert row(env, attempts, task_id=env.lease.owner_id, attempt_id=attempt_id)["state"] == "SETTLED"


@pytest.mark.parametrize(
    "audit,error",
    [
        (FailingUsageFactAudit, "FIXTURE_G02_FAILURE"),
        (FailingRequiredAudit, "FIXTURE_AUDIT_FAILURE"),
    ],
)
def test_g02_or_required_audit_failure_rolls_back_fact_attempt_and_budget(usage_env, audit, error):
    env = usage_env
    attempt_id = sent_attempt(env)
    before = snapshot(env)
    env.service.audit = audit()
    with pytest.raises(RuntimeError, match="^" + error + "$"):
        env.budget.record_model_usage(
            attempt_id,
            total_tokens=30,
            input_tokens=10,
            output_tokens=20,
            currency="USD",
            pricing_version="deepseek-contract-v1",
        )
    assert snapshot(env) == before
    assert count(env, usage_facts, task_id=env.lease.owner_id) == 0
    assert row(env, attempts, task_id=env.lease.owner_id, attempt_id=attempt_id)["state"] == "SENT"
    control = row(env, budgets, task_id=env.lease.owner_id)
    assert (control["used_calls"], control["reserved_calls"]) == (0, 1)
    assert (control["used_tokens"], control["reserved_tokens"]) == (0, 100)
    assert (control["used_cost"], control["reserved_cost"]) == (Decimal("0"), Decimal("0.5"))

    env.service.audit = Audit()
    env.budget.record_model_usage(
        attempt_id,
        total_tokens=30,
        input_tokens=10,
        output_tokens=20,
        currency="USD",
        pricing_version="deepseek-contract-v1",
    )
    assert count(env, usage_facts, task_id=env.lease.owner_id) == 1
