"""C-01 uses real original-task MySQL budget/G02, exclusively OFFLINE Mock provider IO."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
import threading
import time

import pytest
from sqlalchemy import select, update, func

from commerce_hub.adapters.models.mock import MockProvider
from commerce_hub.capabilities.models.gateway import ModelGateway
from commerce_hub.governance.observability.tables import usage_facts, audit_events
from commerce_hub.orchestration.budget import BudgetError, TaskBudgetHandle
from commerce_hub.orchestration.tables import attempts, budgets, tasks
from commerce_hub.orchestration.worker import ExecutionContext
from commerce_hub.scenarios.s01.explanation import reserve_request
from tests.integration.orchestration.test_engineering_foundation import make_foundation, running, owned_row, count, expire_owned_lease
from tests.integration.orchestration.test_engineering_foundation import FailingAudit
from tests.unit.models.support import fixture_bundle

pytestmark = [pytest.mark.mysql, pytest.mark.skipif(os.environ.get("COMMERCE_RUN_MYSQL_TESTS") != "1",
    reason="C-01 opt-in isolated MySQL engineering tests")]


def prepare(make_foundation, **options):
    env = make_foundation(max_calls=4, max_tokens=80000, **options)
    view, lease, budget = running(env)
    task = owned_row(env, tasks, task_id=lease.owner_id)
    context = ExecutionContext(env.service, lease, env.principal, dict(task), threading.Event())
    bundle = fixture_bundle(env.tenant, lease.owner_id)
    return env, context, bundle


def request(context,bundle,attempt="attempt-1",logical="call-1",**kw):
    return reserve_request(context,bundle,logical_call_id=logical,attempt_id=attempt,max_tokens=20000,
        max_cost=Decimal(".01"),trace_id="a"*32,**kw)


def test_mock_success_settles_one_g02_usage_and_duplicate_cannot_resend(make_foundation,monkeypatch):
    # Block the real model transport while leaving authorized MySQL connectivity available.
    import http.client
    monkeypatch.setattr(http.client.HTTPSConnection,"connect",lambda *a:pytest.fail("unauthorized model network"))
    env, context, bundle = prepare(make_foundation)
    req = request(context,bundle)
    provider = MockProvider()
    result = ModelGateway(provider).invoke(req,context,bundle)
    assert result.code=="OK" and result.usageStatus=="KNOWN" and result.usageRef
    state=owned_row(env,budgets,task_id=context.lease.owner_id)
    assert state["used_calls"]==1 and state["reserved_calls"]==0 and state["used_tokens"]==96
    assert state["used_cost"]==Decimal(".0001") and count(env,usage_facts)==1
    assert context.budget.settle("attempt-1",96,".0001",currency="TEST",pricing_version="mock-v1")==result.usageRef
    assert ModelGateway(provider).invoke(req,context,bundle).code=="RESULT_UNAVAILABLE" and provider.calls==1
    with env.database.engine.connect() as conn:
        records=conn.execute(select(audit_events.c.details).filter_by(tenant_id=env.tenant).where(audit_events.c.action.like("MODEL_%"))).scalars().all()
    log=json.dumps(records)
    assert "digests" in log and "mock-v1" in log and "recommendationReasons" not in log
    assert "Synthetic facts only" not in log and "Authorization" not in log


@pytest.mark.parametrize("field,value",[("planVersion","2"),("policyContextRef",{"id":"other","version":"1"}),
    ("allowanceRef",{"tenantId":"REPLACE","id":"other","version":"1"}),
    ("principalRef",{"tenantId":"REPLACE","principalId":"other"}),
    ("snapshotId","other-snapshot"),("participantId","other-participant")])
def test_binding_mismatches_fail_before_send(make_foundation,field,value):
    env,context,bundle=prepare(make_foundation)
    req=request(context,bundle).model_dump()
    if isinstance(value,dict): value={k:env.tenant if v=="REPLACE" else v for k,v in value.items()}
    req[field]=value
    provider=MockProvider()
    result=ModelGateway(provider).invoke(req,context,bundle)
    assert result.status=="TECH_ERROR" and provider.calls==0 and count(env,usage_facts)==0


def test_deadline_cannot_extend_original_task_and_expired_task_never_sends(make_foundation):
    env,context,bundle=prepare(make_foundation)
    req=request(context,bundle).model_dump()
    req["deadline"]=datetime.now(timezone.utc)+timedelta(hours=1)
    provider=MockProvider()
    assert ModelGateway(provider).invoke(req,context,bundle).code=="MODEL_BINDING_DENIED"
    with env.database.engine.begin() as conn:
        conn.execute(update(tasks).filter_by(tenant_id=env.tenant,task_id=context.lease.owner_id)
            .values(deadline=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(seconds=1)))
    result=ModelGateway(provider).invoke(req,context,bundle)
    assert result.code=="DEADLINE_EXCEEDED" and provider.calls==0


def test_unknown_cost_remains_reserved_and_same_logical_retry_is_denied(make_foundation):
    env,context,bundle=prepare(make_foundation)
    provider=MockProvider(mode="unknown")
    req=request(context,bundle)
    result=ModelGateway(provider).invoke(req,context,bundle)
    assert result.code=="OK" and result.usageRef
    state=owned_row(env,budgets,task_id=context.lease.owner_id)
    assert state["reserved_calls"]==0 and state["reserved_tokens"]==20000 and state["reserved_cost"]==Decimal(".01")
    assert state["used_calls"]==1 and count(env,usage_facts)==1
    with pytest.raises(BudgetError,match="USAGE_MUST_BE_RECONCILED"):
        request(context,bundle,attempt="attempt-2")
    other=request(context,bundle,attempt="attempt-other",logical="other-call")
    assert ModelGateway(provider,max_concurrent=4).invoke(other,context,bundle).code=="OK"
    assert provider.calls==2


def test_known_failure_retry_uses_new_attempt_same_task_no_deadline_reset(make_foundation):
    env,context,bundle=prepare(make_foundation)
    req=request(context,bundle)
    assert ModelGateway(MockProvider(mode="refused")).invoke(req,context,bundle).code=="REFUSED"
    original_deadline=context.task["deadline"]
    retry=request(context,bundle,attempt="attempt-2")
    assert ModelGateway(MockProvider()).invoke(retry,context,bundle).code=="OK"
    state=owned_row(env,budgets,task_id=context.lease.owner_id)
    assert state["used_calls"]==2 and count(env,usage_facts)==2
    assert owned_row(env,tasks,task_id=context.lease.owner_id)["deadline"]==original_deadline


def test_cross_gateway_concurrency_limit_is_durable_and_network_outside_locks(make_foundation):
    env,context,bundle=prepare(make_foundation)
    entered,release=threading.Event(),threading.Event()
    first,second=request(context,bundle),request(context,bundle,attempt="attempt-2",logical="call-2")
    provider=MockProvider(entered=entered,release=release)
    with ThreadPoolExecutor() as pool:
        job=pool.submit(ModelGateway(provider).invoke,first,context,bundle)
        assert entered.wait(3)
        try:
            result=ModelGateway(provider).invoke(second,context,bundle)
            assert result.code=="CONCURRENCY_DENIED" and provider.calls==1
            # This SQL write is possible while the provider is held, proving no long O01 transaction.
            view=env.service.read(env.principal,context.lease.owner_id)
            env.service.cancel(env.principal,context.lease.owner_id,"cancel-c01",view["revision"],"b"*32)
            stopped=job.result(timeout=3)
            assert stopped.code in {"TASK_STOPPED", "LEASE_LOST"} and stopped.validatedObject is None
        finally:
            release.set()
    end=time.monotonic()+3
    while time.monotonic()<end and count(env,usage_facts)==0: time.sleep(.02)
    assert count(env,usage_facts)==1


def test_same_logical_two_reserved_attempts_cannot_race_send(make_foundation):
    env,context,bundle=prepare(make_foundation)
    first,second=request(context,bundle),request(context,bundle,attempt="attempt-2")
    entered,release=threading.Event(),threading.Event()
    provider=MockProvider(entered=entered,release=release)
    with ThreadPoolExecutor() as pool:
        job=pool.submit(ModelGateway(provider,max_concurrent=4).invoke,first,context,bundle)
        assert entered.wait(3)
        try:
            assert ModelGateway(provider,max_concurrent=4).invoke(second,context,bundle).code=="USAGE_MUST_BE_RECONCILED"
        finally: release.set()
        assert job.result(timeout=3).code=="OK"
    assert provider.calls==1


def test_short_attempt_deadline_and_late_result_never_publish(make_foundation):
    env,context,bundle=prepare(make_foundation)
    # Leave time for real DB admission, then hold a confirmed send past its original attempt deadline.
    req=request(context,bundle,deadline=datetime.now(timezone.utc)+timedelta(seconds=2))
    entered,release=threading.Event(),threading.Event()
    provider=MockProvider(entered=entered,release=release)
    with ThreadPoolExecutor() as pool:
        job=pool.submit(ModelGateway(provider).invoke,req,context,bundle)
        try:
            assert entered.wait(3)
            result=job.result(timeout=4)
            assert result.code=="TIMEOUT" and result.validatedObject is None
            assert provider.calls==1 and count(env,usage_facts)==0
            assert owned_row(env,attempts)["state"]=="UNKNOWN"
        finally:
            release.set()
    end=time.monotonic()+3
    while time.monotonic()<end and count(env,usage_facts)==0: time.sleep(.02)
    assert count(env,usage_facts)==1 and provider.calls==1
    assert owned_row(env,budgets,task_id=context.lease.owner_id)["used_calls"]==1


def test_restart_uses_original_pending_attempt_and_allowance(make_foundation):
    env,context,bundle=prepare(make_foundation)
    req=request(context,bundle)
    assert ModelGateway(MockProvider(mode="timeout")).invoke(req,context,bundle).code=="TIMEOUT"
    expire_owned_lease(env,context.lease)
    env.queue.recover_expired([env.kind])
    lease=env.queue.claim([env.kind])
    assert lease.attempt==2
    task=env.service.start(lease,env.principal)
    resumed=ExecutionContext(env.service,lease,env.principal,dict(task),threading.Event())
    provider=MockProvider()
    assert ModelGateway(provider).invoke(req,resumed,bundle).code=="USAGE_MUST_BE_RECONCILED" and provider.calls==0
    assert resumed.task["deadline"]==context.task["deadline"]
    assert owned_row(env,budgets,task_id=lease.owner_id)["reserved_calls"]==1


def test_revocation_before_send_is_fail_closed(make_foundation):
    env,context,bundle=prepare(make_foundation)
    req=request(context,bundle)
    with env.database.engine.begin() as conn: env.access.revoke_principal(conn,env.principal)
    provider=MockProvider()
    assert ModelGateway(provider).invoke(req,context,bundle).code=="POLICY_DENIED" and provider.calls==0


@pytest.mark.parametrize("action,sends,expected_state",[("MODEL_SENT",0,"RELEASED"),("USAGE_SETTLED",1,"UNKNOWN")])
def test_required_audit_failure_rolls_back_and_conserves_allowance(make_foundation,action,sends,expected_state):
    env,context,bundle=prepare(make_foundation,audit=FailingAudit(action))
    req=request(context,bundle)
    provider=MockProvider()
    result=ModelGateway(provider).invoke(req,context,bundle)
    assert result.status=="TECH_ERROR" and provider.calls==sends
    assert owned_row(env,attempts,task_id=context.lease.owner_id,attempt_id="attempt-1")["state"]==expected_state
    state=owned_row(env,budgets,task_id=context.lease.owner_id)
    assert state["used_calls"]==0 and count(env,usage_facts)==0
    assert state["reserved_calls"]==sends


def test_budget_exhaustion_is_not_a_free_retry(make_foundation):
    env,context,bundle=prepare(make_foundation,max_cost=Decimal(".01"))
    req=request(context,bundle)
    assert ModelGateway(MockProvider(mode="unknown")).invoke(req,context,bundle).code=="OK"
    with pytest.raises(BudgetError,match="BUDGET_DENIED"):
        request(context,bundle,attempt="attempt-2",logical="other")
