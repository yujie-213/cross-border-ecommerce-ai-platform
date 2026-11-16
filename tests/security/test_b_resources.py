"""B scopes and explicit grants: real MySQL/G01; business identities are synthetic."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select, update

from commerce_hub.entrypoints.http.app import create_app
from commerce_hub.governance.access.b_admin import grant_after_sales, validate_configuration
from commerce_hub.governance.access.b_resources import B_ACTIONS, B_ACTION_KINDS, BResourceScope
from commerce_hub.governance.access.local import LocalAdmin, admins
from commerce_hub.governance.access.service import AccessControl, AccessDenied
from commerce_hub.governance.access.tables import b_resource_grants, grants, principals, sessions
from commerce_hub.governance.observability.service import Audit
from commerce_hub.governance.observability.tables import audit_events
from commerce_hub.infrastructure.work import WorkStore
from commerce_hub.infrastructure.work_tables import work_items
from commerce_hub.orchestration.b_authorization import BTaskAuthorization
from commerce_hub.orchestration.budget import BudgetError, TaskBudgetHandle
from commerce_hub.orchestration.contracts import DomainResult
from commerce_hub.orchestration.service import HandlerSpec, TaskError, TaskService
from commerce_hub.orchestration.tables import attempts, budgets, tasks
from commerce_hub.orchestration.worker import Worker


SOURCE = 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'


def resource(tenant, kind='CASE', **changes):
    return dict(schemaVersion='1.0.0', tenantId=tenant, workspaceId='after-sales-fixture', resourceKind=kind,
        resourceId={'CASE': 'case-fixture', 'POLICY': 'policy-fixture', 'DATASET': 'dataset-fixture'}[kind],
        createParent=False, datasetVersion='v1' if kind == 'DATASET' else None,
        sourceNature=SOURCE, sourceTenant='fixture-source', **changes)


def configuration(tenant):
    scope = dict(schemaVersion='1.0.0', tenantId=tenant, workspaceId='after-sales-fixture', resources=[
        dict(resourceKind=kind, sourceNature=SOURCE, sourceTenant='fixture-source',
             resourceIds=[rid], allowCreate=True, datasetVersions={rid: ['v1']} if kind == 'DATASET' else {})
        for kind, rid in [('CASE', 'case-fixture'), ('POLICY', 'policy-fixture'), ('DATASET', 'dataset-fixture')]])
    config = dict(schemaVersion='1.0.0', configurationVersion='fixture-v1', tenantId=tenant,
        workspaceId='after-sales-fixture', grants={action: deepcopy(scope) for action in B_ACTIONS})
    for action, allowed in config['grants'].items():
        allowed['resources'] = [item for item in allowed['resources'] if item['resourceKind'] in B_ACTION_KINDS[action]]
    return config


class Handler:
    """Engineering fixture only; never registered by the production composition."""
    def validate(self, parameters):
        if parameters != {}:
            raise ValueError('FIXTURE_PARAMETERS_INVALID')

    def run(self, context, parameters):
        context.check()
        context.commit_data(lambda conn: conn.scalar(select(func.utc_timestamp(6))))
        return DomainResult(contractVersion='0.1.0', sourceNature='SIMULATED_ENGINEERING',
            completeness='RULES_ONLY', scope=context.task['scope'], snapshotRef='synthetic-b-fixture',
            dataReport={'fixture': True}, analysisReport={'fixture': True})

    def report_view(self, payload):
        return {'sourceNature': payload['sourceNature'], 'scope': payload['scope'], 'fixture': True}


@pytest.fixture
def b_env(database, mysql_settings):
    tenant = 'b-foundation-' + uuid4().hex
    access = AccessControl(database.engine, 'b-fixture', 'b-fixture', 'fixture-only-signing-key-' + 'x' * 64)
    scope = dict(tenantId=tenant, storeIds=['store'], warehouseIds=['warehouse'], canonicalSkuIds=['sku'], fields=['quantity'])
    admin = LocalAdmin(access, tenant, scope)
    admin.initialize('synthetic-admin-password')
    token, _ = admin.login('admin', 'synthetic-admin-password')
    actor = access.authenticate(token)
    config = configuration(tenant)
    spec = HandlerSpec('B_FIXTURE', '1', 'b.fixture.' + uuid4().hex, Handler(), max_calls=2,
        max_tokens=100, max_cost=Decimal('1'), task_authorization=BTaskAuthorization('CASE', 'b:analyze'))
    legacy = HandlerSpec('ENGINEERING_LEGACY', '1', 'legacy.fixture.' + uuid4().hex, Handler())
    queue = WorkStore(database.engine, lease_seconds=30)
    service = TaskService(database.engine, access, queue, Audit(), {spec.scenario_id: spec, legacy.scenario_id: legacy},
        after_sales_enabled=True)
    settings = mysql_settings.model_copy(update=dict(environment='test', auth_issuer=access.issuer,
        auth_audience=access.audience, auth_signing_key=SecretStr('fixture-only-signing-key-' + 'x' * 64),
        browser_origin='https://testserver', after_sales_enabled=True))
    return SimpleNamespace(database=database, settings=settings, tenant=tenant, access=access, scope=scope,
        resource=resource(tenant), actor=actor, token=token, admin=admin, config=config, spec=spec,
        service=service, queue=queue, kind=spec.work_kind)


def apply(e, *, audit=None, config=None, dry_run=False):
    return grant_after_sales(e.database.engine, audit or Audit(), installation_id='installation-fixture',
        tenant_id=e.tenant, configuration=config or e.config, dry_run=dry_run)


def account_snapshot(e):
    with e.database.engine.connect() as conn:
        return {table.name: [dict(r) for r in conn.execute(select(table).filter_by(tenant_id=e.tenant)
            .order_by(*table.primary_key.columns)).mappings()] for table in [admins, principals, sessions, grants]}


def count(e, table):
    with e.database.engine.connect() as conn:
        return conn.scalar(select(func.count()).select_from(table).filter_by(tenant_id=e.tenant))


def create(e, key=None, **changes):
    return e.service.create(e.actor, key or uuid4().hex, 'B_FIXTURE', changes.get('scope', e.resource), {}, uuid4().hex)


def revoke(e, action):
    with e.database.engine.begin() as conn:
        # Explicit test fixture revocation. Only this newly created test tenant is changed.
        conn.execute(update(b_resource_grants).filter_by(tenant_id=e.tenant, action=action).values(active=False, revision=2))


@pytest.mark.mysql
def test_explicit_dry_run_apply_replay_preserve_every_legacy_account_row(b_env):
    e = b_env
    original = account_snapshot(e)
    with pytest.raises(AccessDenied), e.database.engine.begin() as conn:
        e.access.authorize_b_resource(conn, e.actor, 'b:read', e.resource)
    preview = apply(e, dry_run=True)
    assert len(preview['addedActions']) == len(B_ACTIONS)
    assert count(e, b_resource_grants) == count(e, audit_events) == 0
    result = apply(e)
    assert result['commandKey'] == preview['commandKey']
    assert apply(e)['addedActions'] == []
    assert count(e, b_resource_grants) == count(e, audit_events) == len(B_ACTIONS)
    assert account_snapshot(e) == original
    assert e.access.authenticate(e.token) == e.actor
    with e.database.engine.begin() as conn:
        for action in ['tasks:create', 'tasks:read', 'tasks:cancel', 'engineering:execute', 's01:requisition']:
            e.access.authorize(conn, e.actor, action, e.scope)


@pytest.mark.mysql
def test_configuration_conflict_revocation_and_rollback_do_not_mutate_old_state(b_env):
    e = b_env
    original = account_snapshot(e)
    class BrokenAudit(Audit):
        def record(self, conn, **values):
            super().record(conn, **values)
            raise RuntimeError('FIXTURE_AUDIT_FAILURE')
    with pytest.raises(RuntimeError, match='FIXTURE_AUDIT_FAILURE'):
        apply(e, audit=BrokenAudit())
    assert count(e, b_resource_grants) == count(e, audit_events) == 0
    assert account_snapshot(e) == original
    apply(e)
    altered = deepcopy(e.config)
    altered['grants']['b:read']['resources'][0]['resourceIds'].append('new-resource')
    with pytest.raises(ValueError, match='B_GRANT_CONFLICT'):
        apply(e, config=altered)
    revoke(e, 'b:read')
    with pytest.raises(ValueError, match='B_GRANT_CONFLICT'):
        apply(e)
    with pytest.raises(AccessDenied), e.database.engine.begin() as conn:
        e.access.authorize_b_resource(conn, e.actor, 'b:read', e.resource)
    assert account_snapshot(e) == original


@pytest.mark.mysql
def test_resources_without_sku_parent_create_exact_versions_and_source_boundaries(b_env):
    e = b_env
    apply(e)
    with e.database.engine.begin() as conn:
        for kind in ['CASE', 'POLICY', 'DATASET']:
            requested = resource(e.tenant, kind)
            e.access.authorize_b_resource(conn, e.actor, 'b:read', requested)
            parent = dict(requested, resourceId=None, createParent=True, datasetVersion=None)
            e.access.authorize_b_resource(conn, e.actor, 'b:case:write' if kind == 'CASE' else 'b:policy:write' if kind == 'POLICY' else 'b:dataset:manage', parent)
        for altered in [dict(e.resource, tenantId='other'), dict(e.resource, workspaceId='other'),
                dict(e.resource, resourceId='not-owned'), dict(e.resource, sourceTenant='other'),
                dict(e.resource, sourceNature='MIDDLEWARE_TEACHING_DATA'), dict(e.resource, resourceKind='TEACHER'),
                dict(e.resource, schemaVersion='99'), dict(e.resource, resourceId='*'),
                dict(resource(e.tenant, 'DATASET'), datasetVersion='v2')]:
            with pytest.raises(AccessDenied):
                e.access.authorize_b_resource(conn, e.actor, 'b:read', altered)
        with pytest.raises(AccessDenied):
            e.access.authorize(conn, e.actor, 'tasks:read', e.resource)


@pytest.mark.mysql
def test_b_tasks_create_read_publish_history_and_legacy_compatibility(b_env):
    e = b_env
    apply(e)
    first = create(e, 'replay')
    assert create(e, 'replay')['taskRef'] == first['taskRef']
    tid = first['taskRef']['taskId']
    assert e.service.read(e.actor, tid)['state'] == 'QUEUED'
    assert Worker(e.service).once()
    assert e.service.read(e.actor, tid)['state'] == 'SUCCEEDED'
    assert e.service.read_report(e.actor, tid)['fixture']
    old = e.service.create(e.actor, 'legacy', 'ENGINEERING_LEGACY', e.scope, {}, uuid4().hex)
    listed = e.service.mixed_history(e.actor)['items']
    assert {r['taskRef']['taskId'] for r in listed} == {tid, old['taskRef']['taskId']}
    assert len(e.service.mixed_history(e.actor, workspace_id='after-sales-fixture')['items']) == 1
    revoke(e, 'b:read')
    assert len(e.service.mixed_history(e.actor)['items']) == 1
    for read in [e.service.read, e.service.read_report]:
        with pytest.raises(TaskError, match='NOT_FOUND'):
            read(e.actor, tid)


@pytest.mark.mysql
@pytest.mark.parametrize('action', ['b:tasks:create', 'b:analyze'])
def test_legacy_grants_cannot_authorize_b_task_creation(b_env, action):
    e = b_env
    apply(e)
    revoke(e, action)
    with pytest.raises(AccessDenied):
        create(e)
    assert count(e, tasks) == 0


@pytest.mark.mysql
def test_cancel_module_off_and_unregistered_or_unknown_policy_fail_closed(b_env):
    e = b_env
    apply(e)
    view = create(e)
    tid = view['taskRef']['taskId']
    revoke(e, 'b:tasks:cancel')
    with pytest.raises(AccessDenied):
        e.service.cancel(e.actor, tid, 'cancel', 1, uuid4().hex)
    e.service.after_sales_enabled = False
    assert not Worker(e.service).once()  # Disabled B tasks remain recoverable, not consumed.
    with pytest.raises(TaskError, match='NOT_FOUND'):
        e.service.read(e.actor, tid)
    e.service.after_sales_enabled = True
    e.service.registry['B_FIXTURE'] = replace(e.spec, task_authorization=None)
    with pytest.raises(TaskError, match='NOT_FOUND'):
        e.service.read(e.actor, tid)
    e.service.registry['B_FIXTURE'] = e.spec
    with e.database.engine.begin() as conn:
        conn.execute(update(tasks).filter_by(tenant_id=e.tenant, task_id=tid).values(scope=dict(e.resource, schemaVersion='unknown')))
    assert e.service.mixed_history(e.actor)['items'] == []
    assert Worker(e.service).once()
    with e.database.engine.connect() as conn:
        assert conn.execute(select(tasks.c.state).filter_by(tenant_id=e.tenant, task_id=tid)).scalar_one() == 'FAILED'


@pytest.mark.mysql
def test_cancel_success_replay_and_execution_permission_recheck(b_env):
    e = b_env
    apply(e)
    first = create(e)
    tid = first['taskRef']['taskId']
    assert e.service.cancel(e.actor, tid, 'cancel', 1, uuid4().hex)['state'] == 'CANCELLED'
    assert e.service.cancel(e.actor, tid, 'cancel', 1, uuid4().hex)['state'] == 'CANCELLED'
    second = create(e)
    lease = e.queue.claim([e.kind])
    e.service.start(lease, e.actor)
    revoke(e, 'b:tasks:execute')
    for operation in [lambda: e.service.checkpoint(lease, e.actor, 1),
                      lambda: e.service.execution_transaction(lease, e.actor, 1, lambda conn: None),
                      lambda: TaskBudgetHandle(e.service, lease, e.actor, 1).reserve('call', 'attempt', 10, '0.1'),
                      lambda: e.service.complete(lease, e.actor, 1)]:
        with pytest.raises(AccessDenied):
            operation()
    assert e.service.read(e.actor, second['taskRef']['taskId'])['state'] == 'RUNNING'


@pytest.mark.mysql
def test_recreated_worker_preserves_deadline_allowance_and_unknown_send(b_env):
    e = b_env
    apply(e)
    view = create(e)
    tid = view['taskRef']['taskId']
    lease = e.queue.claim([e.kind])
    e.service.start(lease, e.actor)
    handle = TaskBudgetHandle(e.service, lease, e.actor, 1)
    handle.reserve('logical-original', 'attempt-original', 30, '0.10')
    handle.mark_sent('attempt-original')
    handle.unknown('attempt-original')
    with e.database.engine.connect() as conn:
        original = dict(conn.execute(select(budgets).filter_by(tenant_id=e.tenant, task_id=tid)).mappings().one())
    with e.database.engine.begin() as conn:
        conn.execute(update(work_items).filter_by(tenant_id=e.tenant, work_id=lease.work_id).values(lease_expires=func.utc_timestamp(6)))
    restored = TaskService(e.database.engine, e.access, WorkStore(e.database.engine, 30), Audit(),
        e.service.registry, after_sales_enabled=True)
    restored.queue.recover_expired([e.kind])
    new_lease = restored.queue.claim([e.kind])
    assert new_lease is not None
    restored.start(new_lease, e.actor)
    new_handle = TaskBudgetHandle(restored, new_lease, e.actor, 1)
    with pytest.raises(BudgetError, match='USAGE_MUST_BE_RECONCILED'):
        new_handle.reserve('logical-original', 'attempt-second', 30, '0.10')
    assert restored.read(e.actor, tid)['deadline'] == view['deadline']
    with e.database.engine.connect() as conn:
        assert dict(conn.execute(select(budgets).filter_by(tenant_id=e.tenant, task_id=tid)).mappings().one()) == original
        assert conn.execute(select(attempts.c.state).filter_by(tenant_id=e.tenant, task_id=tid)).scalar_one() == 'UNKNOWN'
    restored.complete(new_lease, e.actor, 1)


@pytest.mark.mysql
def test_session_revocation_and_mixed_cursor_are_current_and_principal_bound(b_env):
    e = b_env
    apply(e)
    for _ in range(3):
        create(e)
    first = e.service.mixed_history(e.actor, limit=1)
    second = e.service.mixed_history(e.actor, limit=1, before=first['nextCursor'])
    assert first['items'][0]['taskRef'] != second['items'][0]['taskRef']
    with pytest.raises(TaskError, match='INVALID_HISTORY_QUERY'):
        e.service.mixed_history(e.actor, before=first['nextCursor'] + 'tampered')
    with pytest.raises(TaskError, match='INVALID_HISTORY_QUERY'):
        e.service.mixed_history(e.actor, before=first['nextCursor'], workspace_id='other')
    with e.database.engine.begin() as conn:
        e.access.revoke_token(conn, e.actor)
    with pytest.raises(AccessDenied):
        e.service.mixed_history(e.actor)
    assert Worker(e.service).once()


@pytest.mark.mysql
def test_shared_http_read_history_cancel_and_no_client_selected_b_scope(b_env):
    e = b_env
    apply(e)
    view = create(e)
    tid = view['taskRef']['taskId']
    headers = {'Authorization': 'Bearer ' + e.token}
    with TestClient(create_app(e.settings, e.service.registry), base_url='https://testserver') as client:
        assert client.get('/api/b/v1/status', headers=headers).json()['status'] == 'FOUNDATION_READY'
        assert client.get('/api/v1/analysis-tasks/' + tid, headers=headers).status_code == 200
        assert len(client.get('/api/b/v1/tasks?workspaceId=after-sales-fixture', headers=headers).json()['items']) == 1
        assert client.get('/api/b/v1/tasks?workspaceId=other', headers=headers).json()['items'] == []
        assert client.get('/api/v1/task-history', headers=headers).status_code == 200
        assert client.post('/api/v1/analysis-tasks', headers=dict(headers, **{'Idempotency-Key': 'untrusted'}),
            json=dict(analysisMode='SINGLE', scenarioId='B_FIXTURE', scope=e.resource, parameters={})).status_code == 422
        assert client.post('/api/v1/analysis-tasks/' + tid + '/cancel', json={'expectedRevision': 1},
            headers=dict(headers, **{'Idempotency-Key': 'http-cancel'})).status_code == 200


@pytest.mark.mysql
def test_dataset_jobs_use_exact_version_and_own_domain_action(b_env):
    e = b_env
    apply(e)
    e.service.registry['B_FIXTURE'] = replace(e.spec,
        task_authorization=BTaskAuthorization('DATASET', 'b:dataset:manage'))
    with pytest.raises(AccessDenied):
        create(e)
    view = create(e, scope=resource(e.tenant, 'DATASET'))
    assert Worker(e.service).once()
    assert e.service.read(e.actor, view['taskRef']['taskId'])['state'] == 'SUCCEEDED'
    revoke(e, 'b:dataset:manage')
    with pytest.raises(AccessDenied):
        create(e, scope=resource(e.tenant, 'DATASET'))


@pytest.mark.mysql
def test_b_cookie_commands_require_existing_csrf_and_disabled_module_keeps_s01_ready(b_env):
    e = b_env
    apply(e)
    tid = create(e)['taskRef']['taskId']
    with TestClient(create_app(e.settings, e.service.registry), base_url='https://testserver') as client:
        client.cookies.set('commerce_session', e.token)
        csrf = e.access.issue_csrf(e.actor)
        client.cookies.set('commerce_csrf', csrf)
        url = '/api/v1/analysis-tasks/' + tid + '/cancel'
        assert client.post(url, json={'expectedRevision': 1}, headers={'Idempotency-Key': 'cookie-cancel'}).status_code == 403
        assert client.post(url, json={'expectedRevision': 1}, headers={
            'Idempotency-Key': 'cookie-cancel', 'Origin': 'https://testserver', 'X-CSRF-Token': csrf}).status_code == 200
        client.app.state.tasks.after_sales_enabled = False
        assert client.get('/api/b/v1/status').json()['status'] == 'DISABLED'
        assert client.get('/api/b/v1/tasks?workspaceId=after-sales-fixture').status_code == 503
        assert client.get('/health/ready').status_code == 200


@pytest.mark.mysql
def test_actual_api_restart_and_killed_independent_b_worker_recover_same_task(b_env):
    import os
    import socket
    import sys
    import time
    import httpx
    from tests.integration.processes.test_foundation_processes import OwnedProcess
    e = b_env
    apply(e)
    view = create(e)
    tid = view['taskRef']['taskId']
    with e.database.engine.connect() as conn:
        original_budget = dict(conn.execute(select(budgets).filter_by(tenant_id=e.tenant, task_id=tid)).mappings().one())
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    environment = dict(os.environ, COMMERCE_ENVIRONMENT='test', COMMERCE_B_ENABLED='true',
        COMMERCE_FIXTURE_KIND=e.kind, COMMERCE_AUTH_ISSUER=e.access.issuer, COMMERCE_AUTH_AUDIENCE=e.access.audience,
        COMMERCE_AUTH_SIGNING_KEY='fixture-only-signing-key-' + 'x' * 64, COMMERCE_LEASE_SECONDS='1',
        COMMERCE_HEARTBEAT_SECONDS='0.15', COMMERCE_POLL_SECONDS='0.05', COMMERCE_LOCAL_ADMIN_ENABLED='false',
        COMMERCE_MODEL_PROVIDER='mock', COMMERCE_MODEL_NETWORK_ENABLED='false')
    processes = []
    client = httpx.Client(base_url=f'http://127.0.0.1:{port}', headers={'Authorization': 'Bearer ' + e.token},
        timeout=3, trust_env=False)
    def start_api():
        process = OwnedProcess([sys.executable, '-m', 'uvicorn', 'tests.support.b_foundation:create_app', '--factory',
            '--host', '127.0.0.1', '--port', str(port), '--no-access-log', '--no-server-header'], environment)
        processes.append(process)
        until = time.monotonic() + 12
        while time.monotonic() < until:
            try:
                if client.get('/health/ready').status_code == 200:
                    return process
            except httpx.TransportError:
                pass
            time.sleep(.05)
        pytest.fail('Owned B API did not become ready; child output withheld')
    def wait_state(wanted):
        until = time.monotonic() + 15
        while time.monotonic() < until:
            response = client.get('/api/v1/analysis-tasks/' + tid)
            assert response.status_code == 200
            if response.json()['state'] == wanted:
                return response.json()
            time.sleep(.05)
        pytest.fail('Timed out waiting for owned B fixture task state')
    try:
        api = start_api()
        assert wait_state('QUEUED')['deadline'] == view['deadline']
        api.stop()
        start_api()
        assert wait_state('QUEUED')['taskRef'] == view['taskRef']
        first = OwnedProcess([sys.executable, '-m', 'tests.support.b_foundation', 'worker'], environment)
        processes.append(first)
        wait_state('RUNNING')
        first.stop(crash=True)
        second = OwnedProcess([sys.executable, '-m', 'tests.support.b_foundation', 'worker'], environment)
        processes.append(second)
        assert wait_state('SUCCEEDED')['deadline'] == view['deadline']
        with e.database.engine.connect() as conn:
            assert dict(conn.execute(select(budgets).filter_by(tenant_id=e.tenant, task_id=tid)).mappings().one()) == original_budget
            work = conn.execute(select(work_items).filter_by(tenant_id=e.tenant)).mappings().one()
            assert work['attempt'] == 2
            assert conn.scalar(select(func.count()).select_from(audit_events).filter_by(
                tenant_id=e.tenant, task_id=tid, action='TASK_COMPLETED')) == 1
    finally:
        client.close()
        for process in processes:
            process.stop()
        for process in processes:
            output = b''.join(process.lines).decode('utf-8', errors='replace')
            assert e.token not in output
            assert e.settings.db_password.get_secret_value() not in output


@pytest.mark.parametrize('changes', [dict(resourceId='*'), dict(resourceKind='TEACHER'), dict(schemaVersion='2'),
    dict(resourceId=None), dict(createParent=True), dict(mode='ERP'), dict(actor='admin')])
def test_b_scope_rejects_unknown_or_implicit_authority(changes):
    with pytest.raises(ValueError):
        BResourceScope.model_validate(dict(resource('fixture'), **changes))


def test_configuration_never_treats_new_actions_as_local_admin_default_grants():
    from commerce_hub.governance.access.service import ALLOWED_ACTIONS
    assert not B_ACTIONS.intersection(ALLOWED_ACTIONS)
    config = configuration('fixture')
    config['grants']['engineering:execute'] = deepcopy(config['grants']['b:read'])
    with pytest.raises(ValueError):
        validate_configuration(config, 'fixture')
