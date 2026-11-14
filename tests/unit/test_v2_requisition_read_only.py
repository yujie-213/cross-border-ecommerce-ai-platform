"""Saved local requisition state remains readable while submission is disabled."""
from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from commerce_hub.entrypoints.http.errors import install_error_handlers
from commerce_hub.entrypoints.http.s01_v2 import register_v2_routes
from commerce_hub.scenarios.s01_v2.handler import collection_scope
from commerce_hub.scenarios.s01_v2.policy import V2Policy
from commerce_hub.orchestration.service import TaskError


def test_disabled_submission_can_read_saved_local_state_without_erp():
    actor = SimpleNamespace(tenant_id='local')
    policy = V2Policy('local', '1', requisition_enabled=False)
    handler = SimpleNamespace(policy=policy, validate_scope=MagicMock())
    connection = MagicMock()
    engine = MagicMock()
    engine.begin.return_value = nullcontext(connection)
    engine.connect.return_value = nullcontext(connection)
    row = dict(operation_id='op', report_id='single', state='SUBMITTED',
               created_at=datetime(2026, 1, 1), updated_at=datetime(2026, 1, 1),
               content=dict(erpId='123', erpStatus='待审核'))
    connection.execute.return_value.mappings.return_value.first.return_value = row
    service = SimpleNamespace(engine=engine, access=MagicMock(), v2_requisitions=None,
        registry={'S01_V2_BATCH': SimpleNamespace(handler=handler)},
        read_report=MagicMock(return_value=dict(scenarioId='S01_V2_SINGLE', scope=collection_scope('local'),
            dataReport=dict(item=dict(entityKey='entity'), catalogManifest=dict(acquisition={})))) )
    app = FastAPI()
    install_error_handlers(app)
    app.state.tasks = service
    register_v2_routes(app, lambda: actor)
    with TestClient(app) as client:
        path = '/api/v1/s01/v2/singles/single/requisition'
        response = client.get(path)
        assert response.status_code == 200
        assert response.json()['erpStatus'] == '待审核'
        connection.execute.return_value.mappings.return_value.first.return_value = None
        connection.execute.return_value.mappings.return_value.all.return_value = []
        empty = client.get(path)
        assert empty.status_code == 200 and empty.json() is None
        with pytest.raises(TaskError, match='REQUISITION_NOT_ENABLED'):
            client.post(path, headers={'Idempotency-Key':'test'},
                json=dict(finalQuantity=8,sourceAcknowledged=True))
    service.access.authorize.assert_called()
