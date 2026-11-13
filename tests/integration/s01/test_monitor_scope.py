from uuid import uuid4
from copy import deepcopy
import pytest
from sqlalchemy import update
from commerce_hub.data.projection.monitor import MonitorRegistry, monitor_scopes
from tests.unit.data.test_owned import owned_case

pytestmark=pytest.mark.mysql


def test_monitor_registry_is_durable_idempotent_and_rejects_version_rewrite(database):
    m,_,_=owned_case();m=m.model_copy(update={'scope':dict(m.scope,tenantId='monitor-'+uuid4().hex)})
    r=MonitorRegistry(database.engine);payload=[m.model_dump(mode='json')]
    digest=r.activate(payload,'fixture-owner')
    assert MonitorRegistry(database.engine).activate(payload,'fixture-owner')==digest
    r.require(m);r.require_scope(m.scope)
    wrong=deepcopy(payload);wrong[0]['monitor']['productId']='999'
    with pytest.raises(ValueError,match='IMMUTABLE_MONITOR_VERSION_CONFLICT'):r.activate(wrong,'fixture-owner')
    with pytest.raises(ValueError,match='MONITOR_SCOPE_NOT_ACTIVE'):r.require_scope(dict(m.scope,canonicalSkuIds=['unregistered']))
    with database.engine.begin() as conn:
        conn.execute(update(monitor_scopes).filter_by(tenant_id=m.scope['tenantId']).values(active=False))
    with pytest.raises(ValueError,match='MONITOR_MEMBER_NOT_ACTIVE'):r.require(m)


def test_monitor_content_integrity_is_checked_on_read(database):
    m,_,_=owned_case();m=m.model_copy(update={'scope':dict(m.scope,tenantId='monitor-'+uuid4().hex)})
    r=MonitorRegistry(database.engine);r.activate([m.model_dump(mode='json')],'fixture-owner')
    with database.engine.begin() as conn:
        conn.execute(update(monitor_scopes).filter_by(tenant_id=m.scope['tenantId']).values(content_digest='0'*64))
    try:
        with pytest.raises(ValueError,match='MONITOR_CONTENT_DIGEST_MISMATCH'):r.mappings()
    finally:
        with database.engine.begin() as conn:
            conn.execute(update(monitor_scopes).filter_by(tenant_id=m.scope['tenantId']).values(active=False))
