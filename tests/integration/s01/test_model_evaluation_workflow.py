"""One persistent evaluation authorization, offline provider, actual isolated MySQL."""
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from commerce_hub.governance.observability.tables import usage_facts
from commerce_hub.orchestration.service import TaskError, TaskService
from commerce_hub.orchestration.tables import attempts, budgets, reports
from commerce_hub.orchestration.worker import Worker
from commerce_hub.scenarios.s01_backend.evaluation import S01ModelEvaluationHandler
from tests.integration.orchestration.test_s01_reports import make_s01, count
from tests.integration.s01.test_backend_workflow import OfflineNaturalProvider
from tests.support.backend import cases

pytestmark = pytest.mark.mysql


def evaluation_environment(make_s01, provider=None):
    env = make_s01()
    authorization = "offline-" + uuid4().hex
    identity = hashlib.sha256(authorization.encode()).hexdigest()[:32]
    env.tenant = "s01-eval-" + identity
    env.scope = dict(env.scope, tenantId=env.tenant)
    with env.database.engine.begin() as conn:
        env.principal = env.access.provision_fixture(conn, tenant_id=env.tenant,
            principal_id="s01-model-evaluator", token_id=identity,
            expires_at=conn.scalar(select(func.utc_timestamp(6))) + timedelta(hours=1),
            grants_by_action={a:env.scope for a in ["tasks:create", "tasks:read", "engineering:execute"]})
    handler = S01ModelEvaluationHandler(list(cases().values()), list("ABCDE"), env.scope,
        "s01-eval-offline", authorization_id=authorization, provider=provider or OfflineNaturalProvider())
    env.spec = replace(env.spec, scenario_id="S01_MODEL_EVALUATION", handler=handler,
        max_calls=5, max_tokens=120000, max_cost=Decimal("1"), cost_currency="USD")
    env.service.registry = {env.spec.scenario_id:env.spec}
    env.parameters = dict(evaluationRef="s01-eval-offline")
    return env


def create_evaluation(env, key=None):
    return env.service.create(env.principal, key or env.spec.handler.command_key,
        env.spec.scenario_id, env.scope, env.parameters, "offline-test")


def test_evaluation_uses_one_task_budget_and_rejects_new_key(make_s01):
    env = evaluation_environment(make_s01)
    with pytest.raises(TaskError, match="INVALID_COMMAND_KEY"):
        create_evaluation(env, "another-budget")
    task_id = create_evaluation(env)["taskRef"]["taskId"]
    assert Worker(env.service).once()
    public = env.service.read_report(env.principal, task_id)
    evaluation = public["analysisReport"]["evaluation"]
    assert evaluation["status"] == "PASS"
    assert [row["caseId"] for row in evaluation["cases"]] == list("ABCDE")
    assert all(row["ai"]["status"] == "AVAILABLE" and row["ai"]["costStatus"] == "UNKNOWN"
        for row in evaluation["cases"])
    assert not {"sourcePackage", "evaluationResults", "inputProjection", "manifest"} & set(public["dataReport"])
    with env.database.engine.connect() as conn:
        budget = conn.execute(select(budgets).filter_by(tenant_id=env.tenant, task_id=task_id)).mappings().one()
    assert budget["used_calls"] == 5 and budget["used_tokens"] == 995
    assert budget["reserved_cost"] == Decimal(".25") and budget["used_cost"] == 0
    assert count(env, attempts) == count(env, usage_facts) == 5
    assert create_evaluation(env)["taskRef"]["taskId"] == task_id
    assert not Worker(env.service).once()
    assert env.spec.handler.provider.calls == 5
    with pytest.raises(TaskError, match="INVALID_COMMAND_KEY"):
        create_evaluation(env, "yet-another-budget")


def test_nonprimary_evaluation_receipt_is_checked_on_read(make_s01):
    env = evaluation_environment(make_s01)
    task_id = create_evaluation(env)["taskRef"]["taskId"]
    assert Worker(env.service).once()
    with env.database.engine.begin() as conn:
        payload = conn.execute(select(reports.c.payload).filter_by(tenant_id=env.tenant, task_id=task_id)).scalar_one()
        changed = deepcopy(payload)
        changed["dataReport"]["evaluationResults"][1]["analysisReport"]["ai"]["usageRef"] = "fake"
        changed["analysisReport"]["evaluation"] = env.spec.handler._summary(changed["dataReport"]["evaluationResults"])
        conn.execute(update(reports).filter_by(tenant_id=env.tenant, task_id=task_id).values(
            payload=changed, fingerprint=TaskService.fingerprint(changed)))
    with pytest.raises(TaskError, match="NOT_FOUND"):
        env.service.read_report(env.principal, task_id)


def test_evaluation_failure_stops_remaining_cases_but_keeps_primary_rule_report(make_s01):
    class FailSecond(OfflineNaturalProvider):
        def invoke(self, request):
            result = super().invoke(request)
            return result.model_copy(update={"content":"{}"}) if self.calls == 2 else result
    env = evaluation_environment(make_s01, FailSecond())
    task_id = create_evaluation(env)["taskRef"]["taskId"]
    assert Worker(env.service).once()
    report = env.service.read_report(env.principal, task_id)
    assert report["dataReport"]["supplyDemand"]["baseline"]["gapQuantity"] == "15"
    assert report["analysisReport"]["ai"]["status"] == "AVAILABLE"
    assert report["analysisReport"]["evaluation"]["status"] == "FAIL"
    assert report["analysisReport"]["evaluation"]["notRunCases"] == list("CDE")
    assert count(env, attempts) == 2
