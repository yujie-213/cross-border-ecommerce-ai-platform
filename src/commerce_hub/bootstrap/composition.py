from commerce_hub.governance.access.service import AccessControl
from commerce_hub.governance.observability.service import Audit
from commerce_hub.infrastructure.work import WorkStore
from commerce_hub.orchestration.service import TaskService


def task_service(database, settings, registry=None):
    if not settings.auth_configured:
        return None
    access = AccessControl(database.engine, settings.auth_issuer, settings.auth_audience,
                           settings.auth_signing_key.get_secret_value())
    service = TaskService(database.engine, access, WorkStore(database.engine, settings.lease_seconds), Audit(), registry,
                       deadline_seconds=settings.task_deadline_seconds, max_attempts=settings.max_delivery_attempts)
    service.requisitions = None
    backend = (registry or {}).get('S01_BACKEND')
    if backend and getattr(backend.handler, 'requisition_client_factory', None):
        from commerce_hub.scenarios.s01_backend.requisition import RequisitionService
        service.requisitions = RequisitionService(service, backend.handler.scope_registry, backend.handler.requisition_client_factory)
    return service
