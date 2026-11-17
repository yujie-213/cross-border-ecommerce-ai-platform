"""Shared API/Worker B assembly. No migrations, grants, source IO or model sends on startup."""
import json
from decimal import Decimal
from pathlib import Path

from commerce_hub.orchestration.service import HandlerSpec,SharedModelAuthorization
from commerce_hub.orchestration.b_authorization import BTaskAuthorization
from commerce_hub.scenarios.after_sales.handler import Handler
from commerce_hub.scenarios.after_sales.source import SourceReader

ROOT=Path(__file__).resolve().parents[3]
PRIVATE=ROOT/'data/private/b-after-sales'


def source_reader(settings):
    from commerce_hub.infrastructure.database import Database
    from commerce_hub.data.projection.monitor import MonitorRegistry
    registry=MonitorRegistry(Database(settings).engine,'s01-owned-teaching-local')
    # Consume the same verified, versioned membership as replenishment. A store
    # grant, a readable catalog or a SKU prefix cannot admit another resource.
    stores={m.storeName:dict(storeId=m.sourceStore,sourceTenant=m.sourceTenant)
        for m in registry.mappings() if m.monitor}
    from commerce_hub.adapters.erp import TeachingERPReader
    from commerce_hub.bootstrap.s01_v2 import erp_config
    reader=SourceReader(lambda:TeachingERPReader(erp_config()),stores,PRIVATE/'source-evidence',owned_provider=registry.mappings,
        supplemental_context=PRIVATE/'customer-context.json')
    from commerce_hub.adapters.erp_customer_voice import TeachingVoiceClient
    reader.voice_client_factory=lambda:TeachingVoiceClient(erp_config())
    return reader


def registry(settings):
    if not settings.after_sales_enabled:return {}
    try:reader=source_reader(settings)
    except (OSError,ValueError,TypeError):reader=None
    provider=None;shared=None
    path=PRIVATE/'model-authorization.json'
    if path.exists() and settings.model_network_enabled and settings.model_provider=='deepseek':
        try:
            auth=json.loads(path.read_text(encoding='utf-8'))
            if (set(auth)!={'authorizationId','maxCalls','maxTokens','maxCostUSD','approvedPurposes'}
                or not auth['authorizationId'].startswith('b-')
                or set(auth['approvedPurposes'])!={'b.case.advice.v1','b.feedback.classify.v1','b.experience.explain.v1'}
                or type(auth['maxCalls']) is not int or type(auth['maxTokens']) is not int):
                raise ValueError('B_MODEL_AUTHORIZATION_INVALID')
            shared=SharedModelAuthorization(auth['authorizationId'],auth['maxCalls'],auth['maxTokens'],Decimal(auth['maxCostUSD']))
            from commerce_hub.adapters.models.evaluation import EvaluationProvider,EvaluationAuthorization
            provider=EvaluationProvider(settings,authorization=EvaluationAuthorization(shared.authorization_id,shared.max_calls,shared.max_cost,Decimal('.05')))
        except (OSError,ValueError,TypeError,KeyError,ArithmeticError):
            provider=None;shared=None
    specs={}
    for scenario,job,kind,action in [
        ('B_CASE_EVIDENCE_V1','evidence','CASE','b:analyze'),('B_CASE_ADVICE_V1','advice','CASE','b:analyze')]:
        enabled=provider is not None and job=='advice'
        calls=3 if job=='advice' else 10
        spec=HandlerSpec(scenario,'1.0.0','b.workflow.'+job+'.v1',Handler(job,source_reader=reader,provider=provider if enabled else None),
            task_authorization=BTaskAuthorization(kind,action),max_calls=calls if enabled else 0,max_tokens=24000*calls if enabled else 0,
            max_cost=Decimal('.05')*calls if enabled else Decimal('0'),policy_version=shared.authorization_id if enabled else 'b-no-model-v1',
            cost_currency='USD' if enabled else None,shared_model_authorization=shared if enabled else None)
        specs[scenario]=spec
    return specs
