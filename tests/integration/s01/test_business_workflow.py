"""Real authorized MySQL/O01/G02; all model IO is an explicit Mock."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from threading import Event
from copy import deepcopy
import json
import time

import pytest
from sqlalchemy import select, update

from commerce_hub.orchestration.worker import Worker, ExecutionContext
from commerce_hub.orchestration.tables import tasks, reports, budgets, attempts
from commerce_hub.governance.observability.tables import usage_facts
from commerce_hub.scenarios.s01_supply_inventory import S01SupplyInventoryHandler, S01MockProvider
from tests.integration.orchestration.test_s01_reports import make_s01, create, count
from tests.support.s01 import example

pytestmark=pytest.mark.mysql


def business(make_s01, provider=None, **handler_options):
    env=make_s01()
    env.spec=replace(env.spec,handler=S01SupplyInventoryHandler(provider,**handler_options),max_calls=1,
        max_tokens=24000,max_cost=Decimal(".01"),policy_version="s01-business-mock-v1")
    env.service.registry={env.spec.scenario_id:env.spec}
    return env


def row(env, table, **keys):
    with env.database.engine.connect() as conn:
        return conn.execute(select(table).filter_by(tenant_id=env.tenant,**keys)).mappings().one()


def test_actual_gateway_settles_original_budget_and_publishes_only_quantity_report(make_s01,monkeypatch):
    import http.client
    monkeypatch.setattr(http.client.HTTPSConnection,"connect",lambda *a:pytest.fail("real model network forbidden"))
    env=business(make_s01)
    task_id=create(env)["taskRef"]["taskId"]
    assert Worker(env.service).once()
    report=env.service.read_report(env.principal,task_id)
    ai=report["analysisReport"]["ai"]
    assert ai["status"]=="AVAILABLE" and ai["usageStatus"]=="KNOWN"
    assert ai["versionBundle"]["contextBundleRef"]["tenantId"]==env.tenant
    assert ai["binding"]["snapshotId"]==report["snapshotRef"]
    assert ai["realModelAcceptance"]=="NOT_RUN" and ai["provider"]=="MOCK"
    assert row(env,budgets,task_id=task_id)["used_calls"]==1 and count(env,usage_facts)==1
    assert "inputProjection" not in report["dataReport"] and "sourceSku" not in str(ai)
    assert create(env)["reportRef"]==report["reportRef"]
    assert env.spec.handler.provider.calls==1 and count(env,reports)==1


@pytest.mark.parametrize("mode",["refused","truncated","json","unknown","exception","timeout"])
def test_gateway_failure_or_unknown_keeps_rule_report_without_new_model_attempt(make_s01,mode):
    env=business(make_s01,S01MockProvider(mode=mode))
    task_id=create(env)["taskRef"]["taskId"]
    assert Worker(env.service).once()
    report=env.service.read_report(env.principal,task_id)
    ai=report["analysisReport"]["ai"]
    assert ai["status"]=="UNAVAILABLE" and ai["explanation"] is None
    assert report["dataReport"]["supplyDemand"]["baseline"]["gapQuantity"]=="15"
    assert count(env,attempts)==1 and env.spec.handler.provider.calls==1
    if mode in {"unknown","exception","timeout"}:
        assert row(env,budgets,task_id=task_id)["reserved_calls"]==1


class WrongFacts(S01MockProvider):
    def __init__(self,fault):super().__init__();self.fault=fault
    def invoke(self,request):
        result=super().invoke(request);value=json.loads(result.content)
        if self.fault=="reference":value["keyEvidence"][0]["supportRefs"]=["not-this-snapshot"]
        elif self.fault=="quality":value["majorRisks"][0]["text"]="Quality passed; purchase allowed."
        elif self.fault=="approval":value["humanConfirmations"][0]["text"]="Purchase is approved."
        else:value["keyEvidence"][0]["text"]={"quantity":"Gap is 999", "date":"Supply date is 2099-01-01", "constraint":"MOQ equals one"}[self.fault]
        return result.model_copy(update={"content":json.dumps(value)})


@pytest.mark.parametrize("fault",["quantity","date","constraint","quality","approval","reference"])
def test_gateway_schema_success_still_requires_domain_semantic_gate(make_s01,fault):
    env=business(make_s01,WrongFacts(fault));task_id=create(env)["taskRef"]["taskId"]
    Worker(env.service).once();report=env.service.read_report(env.principal,task_id)
    assert report["analysisReport"]["ai"]["reason"]=="EXPLANATION_SEMANTICS_REJECTED"
    assert report["analysisReport"]["ai"]["explanation"] is None
    assert report["dataReport"]["supplyDemand"]["baseline"]["gapQuantity"]=="15"


@pytest.mark.parametrize("quality",["UNKNOWN","INVESTIGATE"])
def test_real_workflow_never_allows_ai_to_clear_quality_gate(make_s01,quality):
    env=business(make_s01);value=example();value["policy"]["qualityDisposition"]=quality
    task_id=create(env,value)["taskRef"]["taskId"];Worker(env.service).once()
    report=env.service.read_report(env.principal,task_id)
    assert report["analysisReport"]["ai"]["status"]=="AVAILABLE"
    assert report["completeness"]=="PARTIAL" and report["dataReport"]["supplyDemand"]["candidates"]==[]
    assert report["dataReport"]["scenarioSupplement"]["realAdmission"]=="BLOCKED"


def test_reentry_after_usage_settlement_never_resends_or_invents_explanation(make_s01):
    env=business(make_s01);task_id=create(env)["taskRef"]["taskId"]
    lease=env.queue.claim([env.spec.work_kind]);task=env.service.start(lease,env.principal)
    ctx=ExecutionContext(env.service,lease,env.principal,task,Event())
    first=env.spec.handler.run(ctx,example());second=env.spec.handler.run(ctx,example())
    assert first.analysisReport["ai"]["status"]=="AVAILABLE"
    assert second.analysisReport["ai"]["status"]=="UNAVAILABLE"
    assert second.analysisReport["ai"]["reason"]=="RESULT_UNAVAILABLE"
    assert count(env,usage_facts)==count(env,attempts)==1 and env.spec.handler.provider.calls==1
    env.service.complete(lease,env.principal,1,second)
    assert env.service.read_report(env.principal,task_id)["analysisReport"]["ai"]["status"]=="UNAVAILABLE"


@pytest.mark.parametrize("fault",["cancel","plan","lease"])
def test_late_mock_response_does_not_publish_cancelled_stale_or_lost_task(make_s01,fault):
    from commerce_hub.infrastructure.work_tables import work_items
    from datetime import timedelta
    from sqlalchemy import func
    entered,release=Event(),Event()
    env=business(make_s01,S01MockProvider(entered=entered,release=release))
    task_id=create(env)["taskRef"]["taskId"]
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(Worker(env.service).once)
        assert entered.wait(5)
        if fault=="cancel":
            current=env.service.read(env.principal,task_id)
            env.service.cancel(env.principal,task_id,"cancel-business",current["revision"],"test")
        else:
            with env.database.engine.begin() as conn:
                if fault=="plan":conn.execute(update(tasks).filter_by(tenant_id=env.tenant,task_id=task_id).values(plan_version=2))
                else:conn.execute(update(work_items).filter_by(tenant_id=env.tenant).values(lease_expires=conn.scalar(select(func.utc_timestamp(6)))-timedelta(seconds=1)))
        release.set();assert future.result(timeout=5)
    assert count(env,reports)==0
    until=time.monotonic()+5
    while count(env,usage_facts)!=1 and time.monotonic()<until:time.sleep(.02)
    assert count(env,usage_facts)==1


@pytest.mark.parametrize("field", ["resolvedPromptDigest", "contextDigest", "parametersDigest",
    "outputSchemaDigest", "toolSpecsDigest", "promptContentHash"])
def test_well_formed_digest_tampering_blocks_actual_publish_and_read(make_s01, field):
    from commerce_hub.orchestration.service import TaskError
    env = business(make_s01)
    task_id = create(env)["taskRef"]["taskId"]
    lease = env.queue.claim([env.spec.work_kind])
    task = env.service.start(lease, env.principal)
    ctx = ExecutionContext(env.service, lease, env.principal, task, Event())
    valid = env.spec.handler.run(ctx, example())
    bad = deepcopy(valid)
    original = bad.analysisReport["ai"]["versionBundle"]["digests"][field]
    changed = ("0" if original[0] != "0" else "1") + original[1:]
    assert len(changed) == 64 and int(changed, 16) >= 0 and changed != original
    bad.analysisReport["ai"]["versionBundle"]["digests"][field] = changed
    budget_before = dict(row(env, budgets, task_id=task_id))
    with pytest.raises(TaskError, match="INVALID_DOMAIN_RESULT"):
        env.service.complete(lease, env.principal, 1, bad)
    assert count(env, reports) == 0 and row(env, tasks, task_id=task_id)["state"] == "RUNNING"
    assert dict(row(env, budgets, task_id=task_id)) == budget_before and count(env, usage_facts) == 1
    env.service.complete(lease, env.principal, 1, valid)
    original_view = env.service.read_report(env.principal, task_id)
    persisted = dict(row(env, reports, task_id=task_id))
    payload = deepcopy(persisted["payload"])
    payload["analysisReport"]["ai"]["versionBundle"]["digests"][field] = changed
    with env.database.engine.begin() as conn:
        # Recompute the storage digest: the Handler must reject its own inconsistent version metadata.
        conn.execute(update(reports).filter_by(tenant_id=env.tenant, task_id=task_id).values(
            payload=payload, fingerprint=env.service.fingerprint(payload)))
    with pytest.raises(TaskError, match="NOT_FOUND") as error:
        env.service.read_report(env.principal, task_id)
    assert error.value.status == 404
    with env.database.engine.begin() as conn:
        conn.execute(update(reports).filter_by(tenant_id=env.tenant, task_id=task_id).values(
            payload=persisted["payload"], fingerprint=persisted["fingerprint"]))
    assert env.service.read_report(env.principal, task_id) == original_view
    assert count(env, reports) == count(env, usage_facts) == env.spec.handler.provider.calls == 1
    assert dict(row(env, budgets, task_id=task_id)) == budget_before
