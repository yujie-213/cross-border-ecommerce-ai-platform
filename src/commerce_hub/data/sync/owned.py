"""D01 registered core facts plus bounded formal-purchase discovery; historical replay preserved."""
from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.sync.online import utc_now, MODE


def collect_owned(reader, mapping, context, acquisition_id, *, formal_purchases=False, purchase_proofs=()):
    m, b = mapping, mapping.monitor
    started = utc_now()
    queries = [
        ('product', '/api/v1/products', {'ids': b.productId}),
        ('store', '/api/v1/store-authorizations', {'ids': m.sourceStore}),
        ('warehouse', '/api/v1/warehouses', {'ids': m.sourceWarehouse}),
        ('listing', '/api/v1/listings', {'ids': b.listingId}),
        ('inventory', '/api/v1/inventory', {'ids': ','.join(b.inventoryIds)}),
        ('sales', '/api/v1/sales-orders', {'ids': ','.join(b.salesIds)}),
        ('quotes', '/api/v1/supplier-quotes', {'quote_no': b.quoteNo}),
    ]
    if b.purchaseIds and not formal_purchases:
        queries.append(('purchases', '/api/v1/purchase-orders', {'ids': ','.join(b.purchaseIds)}))
    captures = {}

    def cap(name, operation):
        context.check()
        try:
            value = operation()
            if hasattr(value, 'records'):
                rows, complete, total = list(value.records), value.complete, value.total
            else:
                rows, complete, total = [value], True, 1
            captures[name] = dict(rows=rows, complete=complete, total=total,
                observedAt=utc_now(), fingerprint=fingerprint(rows))
        except ERPError as error:
            captures[name] = dict(rows=[], complete=False, error=error.code, httpStatus=error.status)
        context.check()

    for name, path, parameters in queries:
        cap(name, lambda p=path, v=parameters: reader.read(p, v, page_size=50, max_pages=2))
    if formal_purchases:
        from commerce_hub.data.projection.purchases import FORMAL_STATES, POLICY
        for index, state in enumerate(FORMAL_STATES):
            cap('formal-purchases-' + str(index), lambda s=state: reader.read('/api/v1/purchase-orders',
                dict(warehouse_name=m.warehouseName, field='status_text', q=s, match='exact'), page_size=50, max_pages=5))
        parts = [captures.pop('formal-purchases-' + str(i)) for i in range(len(FORMAL_STATES))]
        rows = [r for part in parts for r in part['rows']]
        captures['purchases'] = dict(rows=rows, complete=all(p['complete'] for p in parts), total=len(rows),
            fingerprint=fingerprint(rows), observedAt=utc_now(), policyVersion=POLICY,
            scopeProofs=list(purchase_proofs), sourceParts=[{k:v for k,v in p.items() if k != 'rows'} for p in parts])
    elif not b.purchaseIds:
        captures['purchases'] = dict(rows=[], complete=True, total=0, fingerprint=fingerprint([]), observedAt=utc_now())
    cap('supplier', lambda: reader.detail('suppliers', b.supplierId))
    for sale_id in b.salesIds:
        name = 'workflow-' + sale_id
        cap(name, lambda i=sale_id: reader.detail('sales-workflow', i))
        row = captures[name]['rows']
        workflow = row[0].get('data', {}) if row else {}
        for shipment in workflow.get('shipments', []):
            outbound = shipment.get('outbound_id')
            if type(outbound) is not int or outbound <= 0:
                captures[name].update(complete=False, error='OUTBOUND_ID_INVALID')
                continue
            cap('ledger-' + str(outbound), lambda i=outbound: reader.read('/api/v1/stock/ledger',
                dict(resource='outbound-orders', record_id=i), page_size=50, max_pages=2))
    receipt = dict(version='s01-online-acquisition-v1', acquisitionId=acquisition_id,
        requestedScope=m.scope, mappingVersion=m.version, inputMode=MODE,
        sourceEnvironment='TEACHING_ERP', acquisitionMethod='NETWORK_READ', startedAt=started,
        completedAt=utc_now(), atomicAcrossSystems=False,
        monitoring=dict(datasetId=b.datasetId, scopeVersion=b.scopeVersion, importBatchId=b.importBatchId,
                        evidenceDigest=b.evidenceDigest, registryMemberDigest=fingerprint(m.model_dump(mode='json'))),
        interfaces={name: {k: v for k, v in c.items() if k != 'rows'} for name, c in captures.items()},
        requests=[{k: v for k, v in e.items() if k != 'parameterNames'} for e in reader.events],
        limitations=['FORMAL_STATES_ONLY_NO_UNAPPROVED_READS' if formal_purchases else 'REGISTERED_IDS_ONLY', 'SHARED_ERP_TENANT_NO_SOURCE_ROW_ISOLATION',
                     'NO_ATOMIC_CROSS_INTERFACE_SNAPSHOT', 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'])
    if formal_purchases:
        receipt['purchasePolicy'] = POLICY
    return captures, receipt
