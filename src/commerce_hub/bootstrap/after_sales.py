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


def source_reader():
    path=PRIVATE/'source-scope.json'
    if not path.exists():return None
    stores=json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(stores,dict) or len(stores)>100 or any(not isinstance(k,str) or not k or not isinstance(v,dict)
        or not {'storeId','sourceTenant'}<=set(v) or any(not isinstance(v[f],str) or not v[f] for f in ('storeId','sourceTenant')) for k,v in stores.items())):
        raise ValueError('B_SOURCE_SCOPE_INVALID')
    from commerce_hub.adapters.erp import TeachingERPReader
    from commerce_hub.bootstrap.s01_v2 import erp_config
    return SourceReader(lambda:TeachingERPReader(erp_config()),stores,PRIVATE/'source-evidence')


def registry(settings):
    if not settings.after_sales_enabled:return {}
    try:reader=source_reader()
    except (OSError,ValueError,TypeError):reader=None
    provider=None;shared=None
    path=PRIVATE/'model-authorization.json'
    if path.exists():
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
        ('B_CASE_EVIDENCE_V1','evidence','CASE','b:analyze'),('B_CASE_ADVICE_V1','advice','CASE','b:analyze'),
        ('B_DATASET_VALIDATE_V1','validate','DATASET','b:dataset:manage'),('B_EXPERIENCE_V1','analysis','DATASET','b:analyze'),
        ('B_TEACHING_BINDING_V1','binding','DATASET','b:binding:manage')]:
        enabled=provider is not None and job in {'advice','analysis'}
        calls=3 if job=='advice' else 10
        spec=HandlerSpec(scenario,'1.0.0','b.workflow.'+job+'.v1',Handler(job,source_reader=reader,provider=provider if enabled else None),
            task_authorization=BTaskAuthorization(kind,action),max_calls=calls if enabled else 0,max_tokens=24000*calls if enabled else 0,
            max_cost=Decimal('.05')*calls if enabled else Decimal('0'),policy_version=shared.authorization_id if enabled else 'b-no-model-v1',
            cost_currency='USD' if enabled else None,shared_model_authorization=shared if enabled else None)
        specs[scenario]=spec
    return specs
