"""Explicit fixed-authorization test assembly; startup never sends model requests."""
from decimal import Decimal
import os
from pathlib import Path
import sys

from commerce_hub.adapters.models.evaluation import EvaluationAuthorization, EvaluationProvider
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.entrypoints.http.app import create_app as app_factory
from commerce_hub.entrypoints.worker.__main__ import run
from commerce_hub.orchestration.service import HandlerSpec
from commerce_hub.scenarios.s01_backend import S01BackendHandler
from commerce_hub.scenarios.s01_backend.evaluation import S01ModelEvaluationHandler
from tools.s01_model_evaluation import (
    FIXED_AUTHORIZATION_ID, _authorization_identity, _catalog_evaluation_ref, evaluation_policy, evaluation_catalog,
)


ROOT = Path(__file__).resolve().parents[3]


def registry(settings):
    if (os.environ.get("COMMERCE_S01_MODEL_EVALUATION_ENABLED") != "true"
        or settings.environment != "test" or settings.model_provider != "deepseek"
        or not settings.model_network_enabled or settings.model_name != "deepseek-flash"
        or settings.model_max_output_tokens != 1024):
        raise ValueError("EXPLICIT_MODEL_EVALUATION_MODE_REQUIRED")
    authorization_id = os.environ.get("COMMERCE_S01_MODEL_EVALUATION_AUTHORIZATION_ID")
    policy = evaluation_policy(authorization_id)
    tenant = policy["tenant"]
    configured = os.environ.get("COMMERCE_S01_MODEL_EVALUATION_CATALOG_PATH")
    if configured:
        case_ids, entries, scope = evaluation_catalog(configured, private_root=ROOT / "data/private", policy=policy)
    else:
        if policy["case_order"] is not None:
            raise ValueError("CONTROLLED_TEACHING_CATALOG_REQUIRED")
        from tests.support.backend import cases
        values = cases()
        case_ids = list("ABCDE")
        entries = [values[key] for key in case_ids]
        scope = dict(S01BackendHandler._prepare(entries[0])[1], tenantId=tenant)
    evaluation_ref = _catalog_evaluation_ref(authorization_id, case_ids, entries)
    if evaluation_ref != os.environ.get("COMMERCE_S01_MODEL_EVALUATION_REF"):
        raise ValueError("FIXED_MODEL_EVALUATION_REF_REQUIRED")
    output_value = os.environ.get("COMMERCE_S01_MODEL_EVALUATION_PRIVATE_OUTPUT")
    output = Path(output_value).resolve() if output_value else None
    if output is None or not output.is_relative_to((ROOT / "data/private").resolve()):
        raise ValueError("PRIVATE_EVALUATION_OUTPUT_REQUIRED")
    authorization = EvaluationAuthorization(authorization_id, policy["max_requests"], policy["max_cost"], policy["request_risk"])
    handler = S01ModelEvaluationHandler(entries, case_ids, scope, evaluation_ref,
        authorization_id=authorization_id, provider=EvaluationProvider(settings, authorization=authorization),
        timeout_seconds=settings.model_timeout_seconds, private_output=output, case_order=policy["case_order"],
        tenant_id=tenant, principal_id=policy["principal_id"], logical_namespace=policy["logical_namespace"])
    spec = HandlerSpec("S01_MODEL_EVALUATION", "0.1.0", "s01.modeleval.v1." + evaluation_ref[-32:], handler,
        max_calls=policy["max_requests"], max_tokens=24000 * policy["max_requests"], max_cost=policy["max_cost"], policy_version="s01-model-evaluation-v1", cost_currency="USD")
    return {spec.scenario_id: spec}


def create_app():
    settings = load_settings().model_copy(update={"max_delivery_attempts": 1, "task_deadline_seconds": 600})
    return app_factory(settings, registry(settings))


if __name__ == "__main__":
    if sys.argv[1:] != ["worker"]:
        raise SystemExit("Use the explicit model evaluation worker command")
    settings = load_settings().model_copy(update={"max_delivery_attempts": 1, "task_deadline_seconds": 600})
    raise SystemExit(run(settings, registry(settings)))
