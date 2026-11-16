"""Trusted HandlerSpec authorization adapter; never selected by HTTP parameters."""
from dataclasses import dataclass

from commerce_hub.governance.access.b_resources import BResourceScope
from commerce_hub.governance.access.service import AccessDenied


@dataclass(frozen=True)
class BTaskAuthorization:
    resource_kind: str
    domain_action: str
    version: str = '1.0.0'

    def __post_init__(self):
        if (self.version != '1.0.0' or (self.resource_kind, self.domain_action) not in {
                ('CASE', 'b:analyze'), ('DATASET', 'b:dataset:manage'), ('DATASET','b:analyze'), ('DATASET','b:binding:manage')}):
            raise ValueError('B_TASK_AUTHORIZATION_INVALID')

    def authorize(self, access, connection, principal, operation, scope):
        try:
            resolved = BResourceScope.model_validate(scope)
        except (ValueError, TypeError):
            raise AccessDenied() from None
        # Jobs operate on already persisted objects, never an arbitrary create parent.
        if resolved.resourceKind != self.resource_kind or resolved.createParent:
            raise AccessDenied()
        action = {'create': 'b:tasks:create', 'read': 'b:tasks:read',
                  'cancel': 'b:tasks:cancel', 'execute': 'b:tasks:execute'}.get(operation)
        if action is None:
            raise AccessDenied()
        access.authorize_b_resource(connection, principal, action, scope)
        access.authorize_b_resource(connection, principal,
            'b:read' if operation == 'read' else self.domain_action, scope)
