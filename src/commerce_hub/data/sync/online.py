"""D01 bounded online teaching ERP collection through the existing read connector."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal
from pydantic import Field
from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.contracts import Contract, Identifier, fingerprint
from commerce_hub.data.sync import read_pages, SourceFailure
from commerce_hub.data.sync.teaching import TeachingReadSource

MODE = 'ONLINE_TEACHING_ERP'
TEACHING_BATCH = 'S01-AI-TEST-20261112'

class OnlineMapping(Contract):
    scope: dict
    sku: str = Field(min_length=1, max_length=128)
    sourceTenant: str = Field(min_length=1, max_length=64)
    sourceStore: str = Field(min_length=1, max_length=64)
    sourceWarehouse: str = Field(min_length=1, max_length=64)
    storeName: str = Field(min_length=1, max_length=128)
    warehouseName: str = Field(min_length=1, max_length=128)
    version: Identifier = 's01-online-map-v1'
    teachingReplay: bool = Field(default=False, strict=True)
    sourceSynthetic: bool = Field(default=True, strict=True)

    def validate_scope(self):
        from commerce_hub.data.admission import AdmissionScope
        value = AdmissionScope.model_validate(self.scope).model_dump(mode='json')
        if value != self.scope or self.teachingReplay and self.sku != TEACHING_BATCH + '-A':
            raise ValueError('ONLINE_MAPPING_NOT_APPROVED')
        return self


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def collect(reader, mapping, context, acquisition_id):
    """Never substitute missing rows. Partial domains survive other domain failures."""
    m = mapping.validate_scope()
    started = utc_now()
    common = dict(field='sku', q=m.sku, match='exact')
    queries = [
        ('inventory', '/api/v1/inventory', dict(common, wid=m.sourceWarehouse, store_id=m.sourceStore), 'GET'),
        ('product', '/api/v1/products', common, 'GET'),
        ('store', '/api/v1/store-authorizations', dict(ids=m.sourceStore), 'GET'),
        ('warehouse', '/api/v1/warehouses', dict(ids=m.sourceWarehouse), 'GET'),
        ('listing', '/api/v1/listings', dict(common, store_name=m.storeName), 'GET'),
    ]
    if m.teachingReplay:
        queries += [(f'sales-{day}', '/api/v1/sales-orders', dict(field='order_sn',
            q=TEACHING_BATCH + f'-SALE-202611{day:02d}', match='exact'), 'GET') for day in range(1, 8)]
        queries += [('purchases', '/api/v1/purchase-orders', dict(order_sn=TEACHING_BATCH+'-PURCHASE-A', match='exact'), 'GET'),
            ('purchase-draft', '/api/v1/purchase-orders', dict(order_sn=TEACHING_BATCH+'-PURCHASE-C', match='exact'), 'GET'),
            ('quality', '/api/v1/inbound-orders', dict(field='order_sn', q=TEACHING_BATCH+'-QC-A', match='exact'), 'GET')]
    else:
        queries += [('sales', '/api/v1/sales-orders', dict(store_name=m.storeName, shipping_warehouse=m.warehouseName), 'GET'),
            ('purchases', '/api/v1/purchase-orders', dict(field='warehouse_name', q=m.warehouseName, match='exact'), 'GET'),
            ('buckets', '/erp/sc/routing/data/local_inventory/inventoryDetails', dict(wid=m.sourceWarehouse, sku=m.sku), 'POST'),
            ('quotes', '/api/v1/supplier-quotes', dict(sku=m.sku), 'GET')]
    captures = {}
    auth_failure = None
    for name, path, parameters, method in queries:
        context.check()
        if auth_failure:
            captures[name] = dict(rows=[], complete=False, error=auth_failure)
            continue
        try:
            source = TeachingReadSource(reader, path, parameters, method=method, max_pages=2)
            rows = read_pages(source, max_pages=1, max_records=100)
            batch = source.batch
            captures[name] = dict(rows=list(rows), complete=batch.complete, total=batch.total,
                fingerprint=batch.fingerprint, observedAt=batch.observed_at)
        except (ERPError, SourceFailure) as exc:
            captures[name] = dict(rows=[], complete=False, error=exc.code, httpStatus=getattr(exc, 'status', None))
            if exc.code in {'ERP_AUTH_REJECTED', 'ERP_CREDENTIALS_MISSING', 'ERP_AUTH_ENVELOPE_REJECTED'}:
                auth_failure = exc.code
        context.check()
    # Only safe metadata is persisted in MySQL/public reports; raw rows stay private.
    receipt = dict(version='s01-online-acquisition-v1', acquisitionId=acquisition_id,
        requestedScope=m.scope, mappingVersion=m.version, inputMode=MODE,
        sourceEnvironment='TEACHING_ERP', acquisitionMethod='NETWORK_READ',
        startedAt=started, completedAt=utc_now(), atomicAcrossSystems=False,
        interfaces={name: {k: v for k,v in cap.items() if k != 'rows'} for name,cap in captures.items()},
        requests=[{k:v for k,v in event.items() if k != 'parameterNames'} for event in reader.events],
        limitations=['BOUNDED_EXACT_AUTHORIZED_MAPPING', 'NO_ATOMIC_CROSS_INTERFACE_SNAPSHOT',
            'TEACHING_DATA_ONLY', 'NO_FIXED_CATALOG_FALLBACK'])
    return captures, receipt


def quantity(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
        return str(number) if number.is_finite() and abs(number) < Decimal('1e12') else None
    except (InvalidOperation, ValueError):
        return None
