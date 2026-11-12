from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
import json
from uuid import uuid4

import pytest

from tools.s01_model_evaluation import (
    FIXED_AUTHORIZATION_ID, STRUCTURED_AUTHORIZATION_ID, evaluation_policy, evaluation_catalog,
    _authorization_identity, _process_environment, main,
)
from commerce_hub.scenarios.s01_backend import S01BackendHandler
from commerce_hub.scenarios.s01_backend.evaluation import S01ModelEvaluationHandler
from tests.support.admission import build_teaching_admission_package
from tests.support.backend import cases


def test_successor_identity_calls_and_budget_are_explicit_and_separate():
    old=evaluation_policy(FIXED_AUTHORIZATION_ID); new=evaluation_policy(STRUCTURED_AUTHORIZATION_ID)
    assert old['max_requests']==5 and new['max_requests']==10
    assert new['max_cost']==Decimal('1') and new['request_risk']==Decimal('.05')
    assert new['tenant']==old['tenant'] and new['principal_id']!=old['principal_id']
    assert new['case_order']==tuple('CDEAB') and old['case_order'] is None
    a=S01BackendHandler(list(cases().values())); b=S01BackendHandler(list(cases().values()),logical_namespace=new['logical_namespace'])
    assert a.natural_logical_call('snapshot-'+'a'*64)!=b.natural_logical_call('snapshot-'+'a'*64)
    assert len(b.natural_logical_call('snapshot-'+'a'*64)+'-1')<=64
    with pytest.raises(ValueError):evaluation_policy('unapproved-new-task')


def test_successor_catalog_reorders_without_modifying_source_payload_or_digest():
    root=Path('data/private')/('successor-test-'+uuid4().hex); root.mkdir(parents=True)
    package=build_teaching_admission_package(); policy=evaluation_policy(STRUCTURED_AUTHORIZATION_ID)
    # Synthetic package scope in this test is trusted source scope; no source rebinding.
    policy=dict(policy,tenant=package['scope']['tenantId'])
    source=dict(schemaVersion='s01-model-evaluation-catalog-v1',authorizationId=FIXED_AUTHORIZATION_ID,tenantId=policy['tenant'],
        entries=[dict(caseId=k,kind='TEACHING_SIMULATION',payload=deepcopy(package)) for k in 'ABCDE'])
    path=root/'catalog.json'; raw=json.dumps(source).encode(); path.write_bytes(raw)
    try:
        ids,entries,scope=evaluation_catalog(path,private_root=root,policy=policy)
        assert ids==list('CDEAB') and all(e['payload']==package for e in entries)
        assert path.read_bytes()==raw and scope==package['scope']
        source['entries'].pop(); path.write_text(json.dumps(source),encoding='utf-8')
        with pytest.raises(ValueError,match='AUTHORIZED_CASE_SET_REQUIRED'):evaluation_catalog(path,private_root=root,policy=policy)
    finally:path.unlink();root.rmdir()


@pytest.mark.parametrize('case_order', [list('ABCDE'),list('CDEAB')])
def test_handler_binds_new_principal_command_and_declared_order(case_order):
    policy=evaluation_policy(STRUCTURED_AUTHORIZATION_ID); values=cases()
    scope=dict(tenantId=policy['tenant'],storeIds=['store-fixture'],warehouseIds=['warehouse-fixture'],canonicalSkuIds=['sku-fixture'],fields=['quantity'])
    h=S01ModelEvaluationHandler([values[k] for k in case_order],case_order,scope,'evaluation-test',authorization_id=STRUCTURED_AUTHORIZATION_ID,
        case_order=case_order,tenant_id=policy['tenant'],principal_id=policy['principal_id'],logical_namespace=policy['logical_namespace'])
    p=SimpleNamespace(tenant_id=scope['tenantId'],principal_id=policy['principal_id'])
    h.validate_command(p,'evaluation-'+_authorization_identity(STRUCTURED_AUTHORIZATION_ID))
    with pytest.raises(ValueError,match='FIXED_EVALUATION_COMMAND_REQUIRED'):h.validate_command(p,'evaluation-'+_authorization_identity(FIXED_AUTHORIZATION_ID))
    with pytest.raises(ValueError):h.validate_command(SimpleNamespace(tenant_id=scope['tenantId'],principal_id='s01-model-evaluator'),h.command_key)
    with pytest.raises(ValueError,match='INVALID_EVALUATION_CASES'):
        S01ModelEvaluationHandler([values[k] for k in case_order],case_order,scope,'test',authorization_id=STRUCTURED_AUTHORIZATION_ID,case_order=list('BACDE'))


def test_successor_cli_rejects_mismatched_budget_before_settings(monkeypatch):
    monkeypatch.setattr('commerce_hub.bootstrap.settings.load_settings',lambda:pytest.fail('read settings'))
    with pytest.raises(ValueError,match='INVALID_EVALUATION_CAP'):
        main(['--execute','--authorization-id',STRUCTURED_AUTHORIZATION_ID,'--max-cost-usd','1','--request-risk-usd','.05','--max-requests','5','--private-output','data/private/not-written.json'])
    env=_process_environment(repository=Path.cwd(),catalog_path=None,evaluation_ref='test',private_output=Path('data/private/not-written.json'),authorization_id=STRUCTURED_AUTHORIZATION_ID)
    assert env['COMMERCE_S01_MODEL_EVALUATION_AUTHORIZATION_ID']==STRUCTURED_AUTHORIZATION_ID
    assert env['COMMERCE_MAX_DELIVERY_ATTEMPTS']=='1'
