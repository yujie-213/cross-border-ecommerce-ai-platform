from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import select

from commerce_hub.orchestration.tables import budgets,attempts
from commerce_hub.orchestration.worker import Worker
from commerce_hub.orchestration.service import TaskError
from commerce_hub.scenarios.s01_backend.evaluation import S01ModelEvaluationHandler
from tests.integration.orchestration.test_s01_reports import make_s01,count
from tests.integration.s01.test_backend_workflow import OfflineNaturalProvider
from tests.support.backend import cases

pytestmark=pytest.mark.mysql


@pytest.mark.parametrize('fail_first',[False,True])
def test_c_first_successor_task_preserves_budget_key_and_safe_failure_stop(make_s01,fail_first):
    class Provider(OfflineNaturalProvider):
        def invoke(self,request):
            result=super().invoke(request)
            return result.model_copy(update={'content':'{}'}) if fail_first else result
    env=make_s01(); ids=list('CDEAB'); values=cases(); authorization='successor-'+env.tenant[-24:]
    handler=S01ModelEvaluationHandler([values[k] for k in ids],ids,env.scope,'successor-offline',authorization_id=authorization,
        provider=Provider(),case_order=ids,tenant_id=env.tenant,principal_id=env.principal.principal_id,logical_namespace='abcdef123456')
    env.spec=replace(env.spec,scenario_id='S01_MODEL_EVALUATION',handler=handler,max_calls=10,max_tokens=240000,max_cost=Decimal('1'),cost_currency='USD')
    env.service.registry={env.spec.scenario_id:env.spec}
    def create(key):return env.service.create(env.principal,key,env.spec.scenario_id,env.scope,dict(evaluationRef='successor-offline'),'test')['taskRef']['taskId']
    task_id=create(handler.command_key);assert Worker(env.service).once()
    report=env.service.read_report(env.principal,task_id); evaluation=report['analysisReport']['evaluation']
    assert evaluation['requestedCases']==ids
    assert [r['caseId'] for r in evaluation['cases']]==(['C'] if fail_first else ids)
    assert evaluation['notRunCases']==(list('DEAB') if fail_first else [])
    assert evaluation['status']==('FAIL' if fail_first else 'PASS')
    with env.database.engine.connect() as c:
        budget=c.execute(select(budgets).filter_by(tenant_id=env.tenant,task_id=task_id)).mappings().one()
        logicals=c.execute(select(attempts.c.logical_call_id).filter_by(tenant_id=env.tenant,task_id=task_id)).scalars().all()
    assert budget['used_calls']==(1 if fail_first else 5) and budget['reserved_cost']==Decimal('.05' if fail_first else '.25')
    assert all(s.startswith('s01-natural-abcdef123456-') for s in logicals)
    assert create(handler.command_key)==task_id and not Worker(env.service).once()
    with pytest.raises(TaskError,match='INVALID_COMMAND_KEY'):create('different-key')
