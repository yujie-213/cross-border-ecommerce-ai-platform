"""Explicit, atomic local-admin B grants; never called by startup or login."""
import hashlib
import json

from sqlalchemy import insert, select

from .b_resources import B_ACTIONS, B_ACTION_KINDS, identifier, normalize_grant
from .local import admins
from .tables import b_resource_grants, principals


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def validate_configuration(config, tenant_id):
    if (not isinstance(config, dict) or set(config) != {'schemaVersion', 'configurationVersion', 'tenantId', 'workspaceId', 'grants'}
            or config['schemaVersion'] != '1.0.0' or config['tenantId'] != tenant_id
            or not identifier(config['configurationVersion']) or not identifier(config['workspaceId'])
            or len(config['workspaceId']) > 64 or not isinstance(config['grants'], dict)
            or not config['grants'] or not set(config['grants']).issubset(B_ACTIONS)):
        raise ValueError('B_GRANT_CONFIGURATION_INVALID')
    for action, grant in config['grants'].items():
        normalize_grant(grant, tenant_id, config['workspaceId'])
        if any(item['resourceKind'] not in B_ACTION_KINDS[action] for item in grant['resources']):
            raise ValueError('B_GRANT_CONFIGURATION_INVALID')
    # Hash canonical parsed content; copying it prevents mutation during a command.
    return json.loads(json.dumps(config))


def grant_after_sales(engine, audit, *, installation_id, tenant_id, configuration, dry_run=True):
    if not identifier(installation_id):
        raise ValueError('B_INSTALLATION_INVALID')
    config = validate_configuration(configuration, tenant_id)
    config_hash = digest(config)
    # Find the real configured administrator. A principal called "admin" is not assumed.
    with engine.connect() as conn:
        admin = conn.execute(select(admins.c.principal_id).filter_by(tenant_id=tenant_id)).scalar_one_or_none()
    if admin is None:
        raise ValueError('ADMIN_NOT_INITIALIZED')
    command_key = digest([installation_id, tenant_id, admin, config['configurationVersion'], config_hash])
    inserted = []
    with engine.begin() as conn:
        current = conn.execute(select(principals).filter_by(tenant_id=tenant_id, principal_id=admin).with_for_update()).mappings().one_or_none()
        if current is None or not current['active']:
            raise ValueError('ADMIN_NOT_ACTIVE')
        # Recheck local ownership after the principal lock, matching reset/login lock order.
        if conn.execute(select(admins.c.principal_id).filter_by(tenant_id=tenant_id)).scalar_one_or_none() != admin:
            raise ValueError('ADMIN_PRINCIPAL_CONFLICT')
        for action in sorted(config['grants']):
            key = dict(tenant_id=tenant_id, principal_id=admin, action=action, workspace_id=config['workspaceId'])
            existing = conn.execute(select(b_resource_grants).filter_by(**key).with_for_update()).mappings().one_or_none()
            if existing is not None:
                if (not existing['active'] or existing['revision'] != 1 or existing['configuration_hash'] != config_hash
                        or existing['command_key'] != command_key or existing['scope'] != config['grants'][action]):
                    raise ValueError('B_GRANT_CONFLICT')
                continue
            inserted.append(action)
            if not dry_run:
                conn.execute(insert(b_resource_grants).values(**key, scope=config['grants'][action],
                    revision=1, active=True, configuration_hash=config_hash, command_key=command_key))
                audit.record(conn, tenant_id=tenant_id, principal_id=admin, action='B_GRANT_ADDED',
                    details=dict(commandKey=command_key, configurationHash=config_hash, action=action,
                                 workspaceId=config['workspaceId']))
    # A fresh connection verifies durable facts rather than trusting insertion receipts.
    if not dry_run:
        with engine.connect() as conn:
            for action, scope in config['grants'].items():
                row = conn.execute(select(b_resource_grants).filter_by(tenant_id=tenant_id, principal_id=admin,
                    action=action, workspace_id=config['workspaceId'])).mappings().one()
                if (row['scope'] != scope or not row['active'] or row['revision'] != 1
                        or row['configuration_hash'] != config_hash or row['command_key'] != command_key):
                    raise ValueError('B_GRANT_READBACK_FAILED')
    return dict(dryRun=dry_run, principalId=admin, workspaceId=config['workspaceId'],
                configurationHash=config_hash, commandKey=command_key, addedActions=inserted,
                unchangedActions=sorted(set(config['grants']) - set(inserted)))
