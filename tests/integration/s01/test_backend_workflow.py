"""New backend consumer fault boundaries using the original real O01/MySQL controls."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from threading import Event
import time

import pytest
from sqlalchemy import select, update, func

from commerce_hub.orchestration.worker import Worker, ExecutionContext
from commerce_hub.orchestration.service import TaskError, TaskService
from commerce_hub.orchestration.tables import reports, tasks, budgets, attempts
from commerce_hub.infrastructure.work_tables import work_items
from commerce_hub.governance.observability.tables import usage_facts
from commerce_hub.scenarios.s01_backend import S01BackendHandler, package_ref
from commerce_hub.scenarios.s01_supply_inventory import S01MockProvider
from commerce_hub.capabilities.models.contracts import ProviderResult, Usage
from tests.integration.orchestration.test_s01_reports import make_s01, count
from tests.support.backend import cases

pytestmark = pytest.mark.mysql


class OfflineNaturalProvider:
    """Documented natural protocol fixture, no transport or billed-cost claim."""
    calls = 0
    def describe_capabilities(self): return frozenset({"structured_output"})
    def preflight(self, payload, cost): pass
    def invoke(self, request):
        import json
        self.calls += 1
        output = {key: [] for key in ("recommendationReasons", "keyEvidence", "majorRisks", "humanConfirmations")}
        for fact in json.loads(request.payload.messages[1].content)["facts"]:
            output[fact["sections"][0]].append(dict(text=fact["allowedPhrases"][-1] + " ["+fact["ref"]+"]", supportRefs=[fact["ref"]]))
        return ProviderResult(status="COMPLETED", finishReason="stop", content=json.dumps(output, ensure_ascii=False),
            actualModelRevision=request.payload.modelRevision, usage=Usage(inputTokens=123, outputTokens=76))


@pytest.mark.parametrize("case_id", list("ABCDE"))
def test_natural_explanation_publishes_and_reads_with_optional_charge_unknown(make_s01, case_id):
    env = make_s01()
    entry = cases()[case_id]
    provider = OfflineNaturalProvider()
    handler = S01BackendHandler([entry], provider=provider, explanation_mode="natural")
    env.spec = replace(env.spec, scenario_id="S01_BACKEND", handler=handler, max_calls=1,
        max_tokens=24000, max_cost=Decimal(".01"), policy_version="backend-test-v1")
    env.service.registry = {env.spec.scenario_id:env.spec}
    task_id = env.service.create(env.principal, "natural-backend", env.spec.scenario_id, env.scope,
        dict(packageRef=package_ref(entry["kind"], entry["payload"])), "test")["taskRef"]["taskId"]
    assert Worker(env.service).once()
    report = env.service.read_report(env.principal, task_id)
    ai = report["analysisReport"]["ai"]
    assert ai["status"] == "AVAILABLE" and ai["tokenUsageStatus"] == "KNOWN" and ai["costStatus"] == "UNKNOWN"
    assert ai["usage"]["totalTokens"] == 199 and ai["usage"]["actualCost"] is None
    with env.database.engine.connect() as conn:
        budget = conn.execute(select(budgets).filter_by(tenant_id=env.tenant,task_id=task_id)).mappings().one()
        stored = conn.execute(select(reports.c.payload).filter_by(tenant_id=env.tenant,task_id=task_id)).scalar_one()
    assert budget["used_calls"] == 1 and budget["used_tokens"] == 199
    assert budget["reserved_cost"] == Decimal(".01")
    changed = deepcopy(stored)
    changed["analysisReport"]["ai"]["explanation"]["majorRisks"][0]["text"] = "质量已通过，采购已批准"
    with pytest.raises(ValueError): handler.report_view(changed)
    assert provider.calls == 1


def environment(make_s01, provider=None):
    env = make_s01()
    entries = list(cases().values())
    env.spec = replace(env.spec, scenario_id="S01_BACKEND", handler=S01BackendHandler(entries, provider=provider or S01MockProvider()),
        max_calls=1, max_tokens=24000, max_cost=Decimal(".01"), policy_version="backend-test-v1")
    env.service.registry = {env.spec.scenario_id:env.spec}
    env.parameters = dict(packageRef=package_ref(entries[0]["kind"], entries[0]["payload"]))
    env.task_id = env.service.create(env.principal, "backend-command", env.spec.scenario_id, env.scope,
        env.parameters, "test")["taskRef"]["taskId"]
    return env


@pytest.mark.parametrize("field,value", [("usageRef","other"),("costStatus","UNKNOWN"),
    ("tokenUsageStatus","UNKNOWN"),("auditRef","other"),("actualModelRevision","other"),
    ("usage",dict(inputTokens=1, outputTokens=2, totalTokens=3, actualCost="0",currency="USD"))])
def test_success_report_usage_receipt_cannot_be_replaced(make_s01, field, value):
    env = environment(make_s01)
    assert Worker(env.service).once()
    with env.database.engine.begin() as conn:
        payload = conn.execute(select(reports.c.payload).filter_by(tenant_id=env.tenant,task_id=env.task_id)).scalar_one()
        changed = deepcopy(payload)
        changed["analysisReport"]["ai"][field] = value
        conn.execute(update(reports).filter_by(tenant_id=env.tenant,task_id=env.task_id).values(
            payload=changed, fingerprint=TaskService.fingerprint(changed)))
    with pytest.raises(TaskError, match="NOT_FOUND"):
        env.service.read_report(env.principal, env.task_id)
    with env.database.engine.begin() as conn:
        conn.execute(update(reports).filter_by(tenant_id=env.tenant,task_id=env.task_id).values(
            payload=payload, fingerprint=TaskService.fingerprint(payload)))
    assert env.service.read_report(env.principal, env.task_id)["analysisReport"]["ai"]["status"] == "AVAILABLE"


def test_publication_checks_usage_receipt_and_later_billing_preserves_report(make_s01):
    env = make_s01()
    entry = cases()["A"]
    handler = S01BackendHandler([entry], provider=OfflineNaturalProvider(), explanation_mode="natural")
    env.spec = replace(env.spec, scenario_id="S01_BACKEND", handler=handler, max_calls=1,
        max_tokens=24000, max_cost=Decimal(".01"), policy_version="backend-test-v1")
    env.service.registry = {env.spec.scenario_id:env.spec}
    params = dict(packageRef=package_ref(entry["kind"], entry["payload"]))
    task_id = env.service.create(env.principal, "natural-receipt", env.spec.scenario_id, env.scope, params, "test")["taskRef"]["taskId"]
    lease = env.queue.claim([env.spec.work_kind])
    task = env.service.start(lease, env.principal)
    context = ExecutionContext(env.service, lease, env.principal, task, Event())
    valid = handler.run(context, params)
    changed = deepcopy(valid)
    changed.analysisReport["ai"]["usage"]["actualCost"] = "0"
    changed.analysisReport["ai"]["usage"]["currency"] = "USD"
    changed.analysisReport["ai"]["costStatus"] = "KNOWN"
    with pytest.raises(TaskError, match="INVALID_DOMAIN_RESULT"):
        env.service.complete(lease, env.principal, 1, changed)
    assert count(env, reports) == 0
    env.service.complete(lease, env.principal, 1, valid)
    before = env.service.read_report(env.principal, task_id)
    logical = "s01-natural-" + valid.snapshotRef[-40:]
    context.budget.record_model_usage(logical + "-1", cost=".0001", currency="USD")
    assert env.service.read_report(env.principal, task_id) == before


@pytest.mark.parametrize("mode", ["exception", "json", "unknown", "timeout", "refused", "model_mismatch"])
def test_model_failure_preserves_calculation_and_no_second_attempt(make_s01, mode):
    env = environment(make_s01, S01MockProvider(mode=mode))
    assert Worker(env.service).once()
    report = env.service.read_report(env.principal, env.task_id)
    assert report["analysisReport"]["ai"]["status"] == "UNAVAILABLE"
    assert report["dataReport"]["supplyDemand"]["candidates"][0]["quantity"] == "20"
    assert env.spec.handler.provider.calls == count(env, attempts) == 1
    assert not Worker(env.service).once()


@pytest.mark.parametrize("fault", ["cancel", "plan", "lease", "deadline"])
def test_late_results_never_publish_after_lifecycle_changes(make_s01, fault):
    entered, release = Event(), Event()
    env = environment(make_s01, S01MockProvider(entered=entered, release=release))
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(Worker(env.service).once)
        assert entered.wait(5)
        if fault == "cancel":
            current = env.service.read(env.principal, env.task_id)
            env.service.cancel(env.principal, env.task_id, "cancel-backend", current["revision"], "test")
        else:
            with env.database.engine.begin() as conn:
                if fault == "plan":
                    conn.execute(update(tasks).filter_by(tenant_id=env.tenant, task_id=env.task_id).values(plan_version=2))
                elif fault == "deadline":
                    conn.execute(update(tasks).filter_by(tenant_id=env.tenant, task_id=env.task_id).values(deadline=conn.scalar(select(func.utc_timestamp(6)))-timedelta(seconds=1)))
                else:
                    conn.execute(update(work_items).filter_by(tenant_id=env.tenant).values(lease_expires=conn.scalar(select(func.utc_timestamp(6)))-timedelta(seconds=1)))
        release.set()
        assert future.result(timeout=8)
    assert count(env, reports) == 0
    until = time.monotonic() + 5
    while count(env, usage_facts) != 1 and time.monotonic() < until:
        time.sleep(.02)
    assert count(env, usage_facts) == 1


def test_self_consistent_package_swap_cannot_publish_or_replace_historical_input(make_s01):
    env = environment(make_s01)
    lease = env.queue.claim([env.spec.work_kind])
    task = env.service.start(lease, env.principal)
    context = ExecutionContext(env.service, lease, env.principal, task, Event())
    valid = env.spec.handler.run(context, env.parameters)
    alternate = cases()["B"]
    # Fully consistent alternate rules output with the SAME tenant/task binding.
    other = S01BackendHandler._rules_result(alternate, env.scope)
    other.analysisReport.update(ai=dict(status="NOT_ATTEMPTED", explanation=None, reason="MODEL_NOT_ENABLED",
        binding=dict(taskRef=dict(tenantId=env.tenant, taskId=env.task_id), planVersion="1", snapshotId=other.snapshotRef, participantId="s01")))
    with pytest.raises(TaskError, match="INVALID_DOMAIN_RESULT"):
        env.service.complete(lease, env.principal, 1, other)
    assert count(env, reports) == 0
    env.service.complete(lease, env.principal, 1, valid)
    with env.database.engine.begin() as conn:
        row = conn.execute(select(reports).filter_by(tenant_id=env.tenant, task_id=env.task_id)).mappings().one()
        original = deepcopy(row["payload"])
        swapped = other.model_dump(mode="json")
        swapped.update({key:original[key] for key in ("taskRef", "reportRef", "planVersion", "scenarioId", "scenarioVersion", "participants")})
        conn.execute(update(reports).filter_by(tenant_id=env.tenant, task_id=env.task_id).values(payload=swapped, fingerprint=TaskService.fingerprint(swapped)))
    with pytest.raises(TaskError, match="NOT_FOUND"):
        env.service.read_report(env.principal, env.task_id)
    with env.database.engine.begin() as conn:
        conn.execute(update(reports).filter_by(tenant_id=env.tenant, task_id=env.task_id).values(payload=original, fingerprint=TaskService.fingerprint(original)))
    assert env.service.read_report(env.principal, env.task_id)["snapshotRef"] == valid.snapshotRef
