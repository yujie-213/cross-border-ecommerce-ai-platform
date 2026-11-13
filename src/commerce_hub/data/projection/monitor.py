"""D02 owned membership. Names never confer membership or ERP-side isolation."""
from datetime import datetime, timezone
import json
from pydantic import Field
from sqlalchemy import Table, Column, String, Integer, Boolean, JSON, DateTime, MetaData, select
from commerce_hub.data.contracts import Contract, Identifier, fingerprint


class ForecastPolicy(Contract):
    version: Identifier = 's01-sma-mvp-v1'
    timezone: str = Field(default='UTC+08:00', pattern=r'^UTC(?:[+-](?:0[0-9]|1[0-4]):[0-5][0-9])?$')
    observationDays: int = Field(default=7, ge=1, le=14, strict=True)
    forecastDays: int = Field(default=7, ge=1, le=14, strict=True)
    coverageDays: int = Field(default=7, ge=1, le=14, strict=True)


class MonitorBinding(Contract):
    datasetId: Identifier
    scopeVersion: int = Field(ge=1, strict=True)
    importBatchId: Identifier
    productId: str = Field(pattern=r'^[1-9][0-9]{0,19}$')
    listingId: str = Field(pattern=r'^[1-9][0-9]{0,19}$')
    supplierId: str = Field(pattern=r'^[1-9][0-9]{0,19}$')
    quoteId: str = Field(pattern=r'^[1-9][0-9]{0,19}$')
    quoteNo: str = Field(min_length=1, max_length=100)
    inventoryIds: tuple[str, ...] = Field(min_length=1, max_length=4)
    salesIds: tuple[str, ...] = Field(min_length=1, max_length=40)
    purchaseIds: tuple[str, ...] = Field(default=(), max_length=20)
    openingQuantity: str
    evidenceDigest: str = Field(pattern=r'^[0-9a-f]{64}$')
    policy: ForecastPolicy = ForecastPolicy()


metadata = MetaData()
monitor_scopes = Table('d02_monitor_scopes', metadata,
    Column('tenant_id', String(64), primary_key=True),
    Column('dataset_id', String(64), primary_key=True),
    Column('scope_version', Integer, primary_key=True),
    Column('active', Boolean, nullable=False),
    Column('content', JSON, nullable=False),
    Column('content_digest', String(64), nullable=False),
    Column('registered_by', String(64), nullable=False),
    Column('registered_at', DateTime, nullable=False),
    mysql_engine='InnoDB', mysql_charset='utf8mb4', mysql_collate='utf8mb4_bin')


class MonitorRegistry:
    def __init__(self, engine, tenant_id=None): self.engine, self.tenant_id = engine, tenant_id

    def activate(self, mappings, actor):
        """Called only by an authorized importer after independent ERP verification."""
        from commerce_hub.data.sync.online import OnlineMapping
        values = [OnlineMapping.model_validate(m).validate_scope() for m in mappings]
        if not values or any(m.monitor is None for m in values):
            raise ValueError('VERIFIED_MONITOR_BINDING_REQUIRED')
        first = values[0]
        key = dict(tenant_id=first.scope['tenantId'], dataset_id=first.monitor.datasetId,
                   scope_version=first.monitor.scopeVersion)
        if self.tenant_id is not None and key['tenant_id'] != self.tenant_id:
            raise ValueError('MONITOR_TENANT_MISMATCH')
        if (any((m.scope['tenantId'], m.monitor.datasetId, m.monitor.scopeVersion) !=
                tuple(key.values()) for m in values) or
                len({fingerprint(m.scope) for m in values}) != len(values)):
            raise ValueError('MONITOR_SCOPE_CONFLICT')
        payload = [m.model_dump(mode='json') for m in values]
        digest = fingerprint(payload)
        with self.engine.begin() as conn:
            rows = conn.execute(select(monitor_scopes).filter_by(
                tenant_id=key['tenant_id'], dataset_id=key['dataset_id']).with_for_update()).mappings().all()
            previous = next((r for r in rows if r['scope_version'] == key['scope_version']), None)
            if previous:
                if previous['content_digest'] != digest or not previous['active']:
                    raise ValueError('IMMUTABLE_MONITOR_VERSION_CONFLICT')
                return digest
            if any(r['active'] for r in rows):
                raise ValueError('EXPLICIT_SCOPE_REVISION_REQUIRED')
            conn.execute(monitor_scopes.insert().values(**key, active=True, content=payload,
                content_digest=digest, registered_by=actor, registered_at=datetime.now(timezone.utc)))
        return digest

    def mappings(self):
        from commerce_hub.data.sync.online import OnlineMapping
        with self.engine.connect() as conn:
            query = select(monitor_scopes).filter_by(active=True)
            if self.tenant_id is not None: query = query.filter_by(tenant_id=self.tenant_id)
            rows = conn.execute(query).mappings().all()
        result = []
        for row in rows:
            content = row['content']
            if isinstance(content, str): content = json.loads(content)
            if fingerprint(content) != row['content_digest']:
                raise ValueError('MONITOR_CONTENT_DIGEST_MISMATCH')
            for value in content:
                m = OnlineMapping.model_validate(value).validate_scope()
                if (m.scope['tenantId'] != row['tenant_id'] or m.monitor.datasetId != row['dataset_id'] or
                        m.monitor.scopeVersion != row['scope_version']):
                    raise ValueError('MONITOR_ROW_BINDING_MISMATCH')
                result.append(m)
        return result

    def require(self, mapping):
        if not any(m == mapping for m in self.mappings()):
            raise ValueError('MONITOR_MEMBER_NOT_ACTIVE')

    def require_scope(self, scope):
        if not any(m.scope == scope for m in self.mappings()):
            raise ValueError('MONITOR_SCOPE_NOT_ACTIVE')
