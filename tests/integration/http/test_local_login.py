"""Real G01/MySQL authentication; synthetic ERP only where explicitly stated."""
import json
from datetime import timedelta
import jwt,pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select,update,func
from commerce_hub.governance.access.local import LocalAdmin,admins,verify_password
from commerce_hub.governance.access.tables import sessions,principals
from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.orchestration.worker import Worker
from tests.integration.orchestration.test_s01_reports import make_s01
from tests.integration.s01.test_v2_workflow import environment

pytestmark=pytest.mark.mysql
PASSWORD='fixture-local-admin-password'

@pytest.fixture
def local(make_s01,tmp_path,mysql_settings):
    e=environment(make_s01,tmp_path)
    e.admin=LocalAdmin(e.access,e.tenant,e.scope)
    e.admin.initialize(PASSWORD)
    settings=mysql_settings.model_copy(update=dict(environment='test',auth_issuer='fixture-issuer',auth_audience='fixture-audience',
        auth_signing_key=SecretStr('fixture-key-'+'x'*64),browser_origin='https://testserver',local_admin_enabled=True,local_app_tenant=e.tenant,local_session_seconds=28800))
    with TestClient(create_app(settings,e.service.registry),base_url='https://testserver') as client:
        client.app.state.tasks=e.service;e.client=client;yield e

def login(e,password=PASSWORD,username='admin'):
    return e.client.post('/api/v1/auth/login',json=dict(username=username,password=password),headers={'Origin':'https://testserver'})

def headers(e):return {'Origin':'https://testserver','X-CSRF-Token':e.client.cookies.get('commerce_csrf'),'Idempotency-Key':'local-fixture'}

def test_password_login_uses_hash_and_matched_persistent_session_deadlines(local):
    e=local
    with e.database.engine.connect() as c:row=c.execute(select(admins).filter_by(tenant_id=e.tenant)).mappings().one()
    assert PASSWORD not in row['password_hash'] and verify_password(PASSWORD,row['password_hash'])
    assert e.client.get('/api/v1/auth/config').json()['mode']=='PASSWORD'
    assert e.client.post('/api/v1/auth/login',json=dict(username='admin',password=PASSWORD)).status_code==403
    response=login(e);assert response.status_code==200
    assert PASSWORD not in response.text and 'commerce_session' not in response.text
    token=e.client.cookies.get('commerce_session');claims=jwt.decode(token,options={'verify_signature':False})
    assert claims['exp']-claims['iat']==28800
    with e.database.engine.connect() as c:expires=c.execute(select(sessions.c.expires_at).filter_by(tenant_id=e.tenant,token_id=claims['jti'])).scalar_one()
    assert int(expires.replace(tzinfo=__import__('datetime').timezone.utc).timestamp())==claims['exp']
    for cookie in response.headers.get_list('set-cookie'):assert 'Max-Age=28800' in cookie and 'Secure' in cookie and 'SameSite=strict' in cookie
    assert 'HttpOnly' in response.headers.get_list('set-cookie')[0]
    assert e.client.get('/api/v1/session').status_code==200
    assert e.client.post('/api/v1/session',headers={'Authorization':'Bearer '+token}).status_code==401

def test_local_login_preserves_csrf_and_v2_batch_never_calls_models_or_writes(local):
    e=local;assert login(e).status_code==200
    assert e.client.post('/api/v1/s01/v2/batches',json={},headers={'Idempotency-Key':'no-csrf'}).status_code==403
    r=e.client.post('/api/v1/s01/v2/batches',json={},headers=headers(e));assert r.status_code==202
    assert Worker(e.service).once()
    tid=r.json()['taskRef']['taskId'];summary=e.client.get('/api/v1/s01/v2/batches/'+tid).json()['summary']
    assert summary['processedCount']==5 and summary['modelCalls']==summary['businessMutations']==e.erp.mutations==0
    csrf=headers(e);old=e.client.cookies.get('commerce_session')
    assert e.client.delete('/api/v1/session',headers=csrf).status_code==200
    e.client.cookies.set('commerce_session',old)
    assert e.client.get('/api/v1/session').status_code==401

def test_login_rotation_expiry_and_reset_revoke_old_sessions_without_resetting_history(local):
    e=local;assert login(e).status_code==200;first=e.client.cookies.get('commerce_session')
    assert login(e).status_code==200;second=e.client.cookies.get('commerce_session');assert first!=second
    with pytest.raises(Exception):e.access.authenticate(first)
    e.admin.initialize('fixture-reset-password',reset=True)
    with pytest.raises(Exception):e.access.authenticate(second)
    assert login(e).status_code==401
    assert login(e,'fixture-reset-password').status_code==200
    token=e.client.cookies.get('commerce_session');claims=jwt.decode(token,options={'verify_signature':False})
    with e.database.engine.begin() as c:c.execute(update(sessions).filter_by(tenant_id=e.tenant,token_id=claims['jti']).values(expires_at=func.utc_timestamp(6)-__import__('sqlalchemy').text('INTERVAL 1 SECOND')))
    response=e.client.get('/api/v1/session');assert response.status_code==401
    assert any('Max-Age=0' in x for x in response.headers.get_list('set-cookie'))

def test_wrong_credentials_and_lock_survive_new_local_admin_instance(local):
    e=local
    for _ in range(5):assert login(e,'fixture-wrong-password').status_code==401
    other=LocalAdmin(e.access,e.tenant,e.scope)
    with pytest.raises(Exception,match='LOGIN_REJECTED'):other.login('admin',PASSWORD)
    with e.database.engine.begin() as c:c.execute(update(admins).filter_by(tenant_id=e.tenant).values(locked_until=func.utc_timestamp(6)-__import__('sqlalchemy').text('INTERVAL 1 SECOND')))
    assert login(e).status_code==200
    with pytest.raises(ValueError,match='ALREADY_INITIALIZED'):e.admin.initialize('fixture-overwrite-password')
    assert login(e).status_code==200

def test_password_errors_do_not_echo_secrets_or_accept_untrusted_origin(local):
    e=local
    for body in [dict(username='admin',password=PASSWORD,role='super'),dict(username='admin',password={'secret':PASSWORD})]:
        response=e.client.post('/api/v1/auth/login',json=body,headers={'Origin':'https://testserver'})
        assert response.status_code==422 and PASSWORD not in response.text
    assert e.client.post('/api/v1/auth/login',json=dict(username='admin',password=PASSWORD),headers={'Origin':'https://evil.invalid'}).status_code==403
    assert login(e,username='someone').status_code==401
