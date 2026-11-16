"""G01 B resource scopes. Callers must resolve ownership before constructing a scope.

There are deliberately no SKU sentinels, wildcard IDs, teacher assets or implicit ERP
permissions here. Source reads remain an additional explicit constraint.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .service import AccessDenied
from .tables import b_resource_grants


B_ACTIONS = frozenset({
    'b:read', 'b:case:write', 'b:case:review', 'b:analyze',
    'b:policy:write', 'b:policy:publish', 'b:dataset:manage',
    'b:tasks:create', 'b:tasks:read', 'b:tasks:cancel', 'b:tasks:execute',
})
RESOURCE_KINDS = Literal['CASE', 'POLICY', 'DATASET']
SOURCE_NATURES = Literal['TEACHING_ERP_OBSERVED', 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP', 'MIDDLEWARE_TEACHING_DATA']
B_ACTION_KINDS = {action: frozenset({'CASE'} if action.startswith('b:case:') else
    {'POLICY'} if action.startswith('b:policy:') else {'DATASET'} if action == 'b:dataset:manage'
    else {'CASE', 'DATASET'} if action == 'b:analyze' else {'CASE', 'POLICY', 'DATASET'}) for action in B_ACTIONS}


def identifier(value):
    return isinstance(value, str) and 1 <= len(value) <= 128 and '*' not in value and not any(ord(c) < 32 for c in value)


def identifiers(values):
    return isinstance(values, list) and len(values) <= 100 and all(identifier(v) for v in values) and len(set(values)) == len(values)


class BResourceScope(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, strict=True, hide_input_in_errors=True)
    schemaVersion: Literal['1.0.0']
    tenantId: str = Field(min_length=1, max_length=64)
    workspaceId: str = Field(min_length=1, max_length=64)
    resourceKind: RESOURCE_KINDS
    resourceId: str | None = None
    createParent: bool = False
    datasetVersion: str | None = None
    sourceNature: SOURCE_NATURES
    sourceTenant: str = Field(min_length=1, max_length=64)

    @model_validator(mode='after')
    def explicit_resource(self):
        if (not all(identifier(v) for v in [self.tenantId, self.workspaceId, self.sourceTenant])
                or self.createParent == (self.resourceId is not None)
                or self.resourceId is not None and not identifier(self.resourceId)
                or self.datasetVersion is not None and not identifier(self.datasetVersion)
                or self.resourceKind != 'DATASET' and self.datasetVersion is not None
                or self.resourceKind == 'DATASET' and not self.createParent and self.datasetVersion is None
                or self.createParent and self.datasetVersion is not None):
            raise ValueError('B_RESOURCE_SCOPE_INVALID')
        return self


def normalize_grant(value, tenant_id, workspace_id):
    """Validate local explicit configuration, never accept this shape over business HTTP."""
    required = {'schemaVersion', 'tenantId', 'workspaceId', 'resources'}
    if (not isinstance(value, dict) or set(value) != required or value['schemaVersion'] != '1.0.0'
            or value['tenantId'] != tenant_id or value['workspaceId'] != workspace_id
            or not all(identifier(v) and len(v) <= 64 for v in [tenant_id, workspace_id])
            or not isinstance(value['resources'], list) or not 1 <= len(value['resources']) <= 100):
        raise ValueError('B_GRANT_INVALID')
    seen = set()
    for item in value['resources']:
        if not isinstance(item, dict) or set(item) != {'resourceKind', 'sourceNature', 'sourceTenant', 'resourceIds', 'allowCreate', 'datasetVersions'}:
            raise ValueError('B_GRANT_INVALID')
        key = (item['resourceKind'], item['sourceNature'], item['sourceTenant'])
        if (item['resourceKind'] not in {'CASE', 'POLICY', 'DATASET'}
                or item['sourceNature'] not in {'TEACHING_ERP_OBSERVED', 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP', 'MIDDLEWARE_TEACHING_DATA'}
                or not identifier(item['sourceTenant']) or len(item['sourceTenant']) > 64 or key in seen
                or not identifiers(item['resourceIds']) or type(item['allowCreate']) is not bool
                or not isinstance(item['datasetVersions'], dict)):
            raise ValueError('B_GRANT_INVALID')
        seen.add(key)
        versions = item['datasetVersions']
        if item['resourceKind'] == 'DATASET':
            if set(versions) != set(item['resourceIds']) or any(not identifiers(v) or not v for v in versions.values()):
                raise ValueError('B_GRANT_INVALID')
        elif versions:
            raise ValueError('B_GRANT_INVALID')
    return value


def authorize_b_resource(access, connection, principal, action, resource_scope, *, lock=True):
    if action not in B_ACTIONS:
        raise AccessDenied()
    try:
        requested = BResourceScope.model_validate(resource_scope)
        if requested.tenantId != principal.tenant_id or requested.resourceKind not in B_ACTION_KINDS[action]:
            raise AccessDenied()
        access._assert_current(connection, principal, lock=lock)
        query = select(b_resource_grants).filter_by(tenant_id=principal.tenant_id,
            principal_id=principal.principal_id, action=action, workspace_id=requested.workspaceId)
        if lock:
            query = query.with_for_update()
        row = connection.execute(query).mappings().one_or_none()
        if row is None or not row['active']:
            raise AccessDenied()
        grant = normalize_grant(row['scope'], principal.tenant_id, requested.workspaceId)
        for item in grant['resources']:
            if (item['resourceKind'], item['sourceNature'], item['sourceTenant']) != (
                    requested.resourceKind, requested.sourceNature, requested.sourceTenant):
                continue
            if requested.createParent and item['allowCreate']:
                return
            if not requested.createParent and requested.resourceId in item['resourceIds']:
                if requested.resourceKind != 'DATASET' or requested.datasetVersion in item['datasetVersions'][requested.resourceId]:
                    return
        raise AccessDenied()
    except SQLAlchemyError:
        raise AccessDenied('AUTH_BACKEND_UNAVAILABLE') from None
    except (ValueError, TypeError, KeyError):
        raise AccessDenied() from None
