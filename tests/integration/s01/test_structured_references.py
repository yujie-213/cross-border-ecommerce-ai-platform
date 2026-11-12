"""Structured-only outputs still pass A01/O01/G02 and publication gates, never real models."""
from dataclasses import replace
from decimal import Decimal
import json

import pytest
from sqlalchemy import select

from commerce_hub.orchestration.worker import Worker
from commerce_hub.orchestration.tables import budgets
from commerce_hub.scenarios.s01_backend import S01BackendHandler, package_ref
from tests.integration.orchestration.test_s01_reports import make_s01
from tests.integration.s01.test_backend_workflow import OfflineNaturalProvider
from tests.support.backend import cases

pytestmark = pytest.mark.mysql


@pytest.mark.parametrize('case_id,fault', [('A', None), ('C', None), ('E', None), ('A', 'quantity'), ('A', 'reference'), ('E', 'approval')])
def test_structured_only_explanation_uses_existing_accounting_and_safe_fallback(make_s01, case_id, fault):
    class StructuredProvider(OfflineNaturalProvider):
        def invoke(self, request):
            result = super().invoke(request)
            value = json.loads(result.content)
            for items in value.values():
                for item in items:
                    item['text'] = item['text'].removesuffix(' [' + item['supportRefs'][0] + ']')
            if fault == 'quantity': value['recommendationReasons'][0]['text'] = '补货候选数量为999件'
            if fault == 'reference': value['keyEvidence'][0]['supportRefs'] = ['cross-task:baseline']
            if fault == 'approval': value['majorRisks'][0]['text'] = '质量已解除，采购可以执行'
            return result.model_copy(update={'content': json.dumps(value, ensure_ascii=False)})
    env = make_s01(); entry = cases()[case_id]; provider = StructuredProvider()
    env.spec = replace(env.spec, scenario_id='S01_BACKEND', handler=S01BackendHandler([entry], provider=provider, explanation_mode='natural'),
        max_calls=1, max_tokens=24000, max_cost=Decimal('.01'), policy_version='backend-test-v1')
    env.service.registry = {env.spec.scenario_id: env.spec}
    task_id = env.service.create(env.principal, 'structured-only', env.spec.scenario_id, env.scope,
        dict(packageRef=package_ref(entry['kind'],entry['payload'])), 'test')['taskRef']['taskId']
    assert Worker(env.service).once()
    report = env.service.read_report(env.principal, task_id)
    ai = report['analysisReport']['ai']
    assert ai['semanticPolicy'] == 's01-controlled-natural-v2'
    assert ai['versionBundle']['promptRef']['version'] == 'controlled-2'
    assert ai['status'] == ('UNAVAILABLE' if fault else 'AVAILABLE')
    if fault:
        assert ai['reason'] == 'INVALID_OUTPUT' and ai['explanation'] is None
    else:
        assert all('[' not in item['text'] for items in ai['explanation'].values() for item in items)
    assert report['dataReport']['scenarioSupplement']['procurementEligible'] is False
    assert ai['costStatus'] == 'UNKNOWN' and ai['usage']['totalTokens'] == 199
    with env.database.engine.connect() as conn:
        budget = conn.execute(select(budgets).filter_by(tenant_id=env.tenant,task_id=task_id)).mappings().one()
    assert budget['used_calls'] == 1 and budget['used_tokens'] == 199 and budget['reserved_cost'] == Decimal('.01')
    assert provider.calls == 1 and not Worker(env.service).once()
