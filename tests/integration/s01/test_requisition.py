"""Real MySQL/O01/G01/G02; synthetic ERP transport, no live writes."""
from dataclasses import replace
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import select, update, delete, func
from commerce_hub.governance.access import AccessDenied
from commerce_hub.governance.access.tables import grants
from commerce_hub.orchestration.worker import Worker
from commerce_hub.orchestration.service import TaskError
from commerce_hub.scenarios.s01_backend.online import OnlineS01Handler
from commerce_hub.scenarios.s01_backend.requisition import RequisitionService
from commerce_hub.scenarios.s01_backend.requisition_store import requisitions
from tests.integration.orchestration.test_s01_reports import make_s01, count
from tests.support.p3_requisition import FixtureERP, FixtureRegistry

pytestmark = pytest.mark.mysql


def environment(make_s01, *, allow=True):
    env = make_s01();erp = FixtureERP(env.scope);registry = FixtureRegistry(erp.mapping)
    env.spec = replace(env.spec, scenario_id='S01_BACKEND',handler=OnlineS01Handler([erp.mapping],lambda *_:erp,
        scope_registry=registry,formal_purchases=True))
    env.service.registry = {env.spec.scenario_id:env.spec}
    if allow:
        with env.database.engine.begin() as conn:
            conn.execute(grants.insert().values(tenant_id=env.tenant,principal_id=env.principal.principal_id,action='s01:requisition',scope=env.scope))
    env.erp, env.registry = erp, registry
    env.requisitions = RequisitionService(env.service,registry,lambda *_:erp)
    view = env.service.create(env.principal,'analysis','S01_BACKEND',env.scope,dict(inputMode='ONLINE_TEACHING_ERP'),'fixture')
    assert Worker(env.service).once()
    env.tid = view['taskRef']['taskId']
    env.report = env.service.read_report(env.principal,env.tid)
    assert env.report['dataReport']['supplyDemand']['candidates'][0]['quantity'] == '48'
    env.confirm = lambda quantity=48, reason='', key='confirm':env.requisitions.confirm(env.principal,env.tid,key,quantity,reason,'fixture')
    return env


def test_create_submit_independent_readback_and_restart_replay(make_s01):
    e = environment(make_s01)
    result = e.confirm()
    assert result['state'] == 'SUBMITTED' and result['erpStatus'] == '待审核'
    assert result['erpId'] == '91' and result['aiQuantity'] == '48' and result['finalQuantity'] == 48
    e.requisitions = RequisitionService(e.service,e.registry,lambda *_:e.erp)
    assert e.confirm() == result and e.confirm(key='different-same-action') == result
    assert e.erp.creates == e.erp.submits == count(e,requisitions) == 1
    assert any(x[1] == 'read-requisition' for x in e.erp.calls)
    assert e.service.read_report(e.principal,e.tid) == e.report
    with pytest.raises(TaskError,match='REQUISITION_COMMAND_CONFLICT'):e.confirm(56,'more')


@pytest.mark.parametrize('qty,reason,code',[(36,'','MOQ_OR_CARTON'),(8,'','MOQ_OR_CARTON'),(56,'','ADJUSTMENT_REASON')])
def test_hard_constraints_reject_before_any_erp_write(make_s01,qty,reason,code):
    e = environment(make_s01)
    with pytest.raises(TaskError,match=code):e.confirm(qty,reason)
    assert e.erp.creates == e.erp.submits == count(e,requisitions) == 0


def test_adjusted_quantity_reason_preserved_without_changing_ai(make_s01):
    e = environment(make_s01)
    r = e.confirm(56,'fixture business reason')
    assert r['state'] == 'SUBMITTED' and r['aiQuantity'] == '48' and r['finalQuantity'] == 56
    assert e.erp.requisition['item_list'][0]['quantity'] == 56


def test_read_permission_does_not_grant_erp_write(make_s01):
    e = environment(make_s01,allow=False)
    with pytest.raises(AccessDenied):e.confirm()
    assert e.erp.creates == 0 and e.requisitions.read(e.principal,e.tid) is None


def test_live_constraint_drift_requires_new_analysis(make_s01):
    e = environment(make_s01)
    e.erp.captures['quotes']['rows'][0]['lead_days'] = 3
    r = e.confirm()
    assert r['state'] == 'BLOCKED' and r['errorCode'] == 'ANALYSIS_CHANGED_REANALYZE'
    assert e.erp.creates == 0


@pytest.mark.parametrize('stage',['create','submit'])
def test_lost_write_ack_reconciles_original_and_never_duplicates(make_s01,stage):
    e = environment(make_s01)
    if stage == 'create':e.erp.create_fault = 'lost-ack'
    else:e.erp.submit_fault = 'lost-ack'
    assert e.confirm()['state'] == 'SUBMITTED'
    assert e.confirm()['state'] == 'SUBMITTED'
    assert e.erp.creates == e.erp.submits == 1


def test_unknown_creation_not_found_never_blindly_resends(make_s01):
    e = environment(make_s01);e.erp.create_fault = 'not-sent'
    assert e.confirm()['state'] == 'CREATE_UNKNOWN'
    assert e.confirm()['state'] == 'CREATE_UNKNOWN'
    assert e.erp.creates == 1 and e.erp.submits == 0


def test_unknown_submit_can_resume_same_id_after_readback(make_s01):
    e = environment(make_s01);e.erp.submit_fault = 'not-sent'
    assert e.confirm()['state'] == 'SUBMIT_UNKNOWN'
    e.erp.submit_fault = None
    assert e.confirm()['state'] == 'SUBMITTED'
    assert e.erp.creates == 1 and e.erp.submits == 2


def test_concurrent_double_click_only_one_network_create(make_s01):
    e = environment(make_s01);entered, release = Event(), Event()
    def hold():entered.set();assert release.wait(8)
    e.erp.on_create = hold
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(e.confirm)
        assert entered.wait(8)
        second = pool.submit(e.confirm).result(timeout=5)
        assert second['state'] == 'CREATING'
        release.set()
        assert first.result(timeout=8)['state'] == 'SUBMITTED'
    assert e.erp.creates == e.erp.submits == 1


def test_midflight_revocation_preserves_draft_but_never_submits(make_s01):
    e = environment(make_s01)
    def revoke():
        with e.database.engine.begin() as conn:
            conn.execute(delete(grants).filter_by(tenant_id=e.tenant,action='s01:requisition'))
    e.erp.on_create = revoke
    r = e.confirm()
    assert r['state'] == 'SUBMIT_UNKNOWN' and e.erp.creates == 1 and e.erp.submits == 0
    with pytest.raises(AccessDenied): e.confirm()


@pytest.mark.parametrize('stage,code',[('create','ERP_CREATE_REJECTED_HTTP_400'),('submit','ERP_SUBMIT_REJECTED_HTTP_409')])
def test_known_erp_rejection_is_distinct_from_unknown_and_not_blindly_retried(make_s01,stage,code):
    e = environment(make_s01)
    if stage == 'create': e.erp.create_fault = 'rejected'
    else: e.erp.submit_fault = 'rejected'
    r = e.confirm()
    assert r['state'] == 'BLOCKED' and r['errorCode'] == code
    assert e.confirm() == r and e.erp.creates == 1 and e.erp.submits == (stage == 'submit')


@pytest.mark.parametrize('stage',['create','submit'])
def test_readback_outage_then_new_service_resumes_durable_original_phase(make_s01,stage):
    e = environment(make_s01)
    if stage == 'create':
        e.erp.on_create = lambda: setattr(e.erp,'read_fault',True)
    else:
        original = e.erp.submit_requisition
        def submit(erp_id):
            result = original(erp_id);e.erp.read_fault = True;return result
        e.erp.submit_requisition = submit
    assert e.confirm()['state'] in {'CREATE_UNKNOWN','SUBMIT_UNKNOWN'}
    e.erp.read_fault = False;e.erp.on_create = None
    e.requisitions = RequisitionService(e.service,e.registry,lambda *_:e.erp)
    assert e.confirm()['state'] == 'SUBMITTED'
    assert e.erp.creates == e.erp.submits == 1


def test_http_csrf_fields_result_and_current_scope_authority(make_s01,mysql_settings):
    from fastapi.testclient import TestClient
    from pydantic import SecretStr
    import jwt
    from datetime import datetime, timezone
    from commerce_hub.entrypoints.http.app import create_app
    e = environment(make_s01)
    now = datetime.now(timezone.utc)
    settings = mysql_settings.model_copy(update=dict(environment='test',auth_issuer='fixture-issuer',auth_audience='fixture-audience',
        auth_signing_key=SecretStr('fixture-key-'+'x'*64),browser_origin='https://testserver'))
    token = jwt.encode(dict(iss='fixture-issuer',aud='fixture-audience',sub=e.principal.principal_id,tid=e.tenant,
        jti=e.principal.token_id,rev=1,iat=int(now.timestamp()),nbf=int(now.timestamp())-1,exp=int(now.timestamp())+600),
        'fixture-key-'+'x'*64,algorithm='HS256')
    with TestClient(create_app(settings,e.service.registry),base_url='https://testserver') as client:
        client.app.state.tasks = e.service
        e.service.requisitions = e.requisitions
        path = '/api/v1/analysis-tasks/'+e.tid+'/requisition'
        assert client.post(path,json=dict(finalQuantity=48),headers={'Idempotency-Key':'fixture'}).status_code == 401
        assert client.post('/api/v1/session',headers={'Authorization':'Bearer '+token}).status_code == 200
        assert client.post(path,json=dict(finalQuantity=48),headers={'Idempotency-Key':'fixture'}).status_code == 403
        headers = {'Idempotency-Key':'fixture','X-CSRF-Token':client.cookies.get('commerce_csrf'),'Origin':'https://testserver'}
        for bad in [dict(finalQuantity=True),dict(finalQuantity=48,tenantId='foreign'),dict(finalQuantity=48,price=1),dict(finalQuantity=48.5)]:
            assert client.post(path,json=bad,headers=headers).status_code == 422
        r = client.post(path,json=dict(finalQuantity=48),headers=headers)
        assert r.status_code == 200 and r.json()['state'] == 'SUBMITTED'
        assert client.get(path).json() == r.json()
        assert client.post(path,json=dict(finalQuantity=48),headers=headers).json() == r.json()
        assert e.erp.creates == e.erp.submits == 1
