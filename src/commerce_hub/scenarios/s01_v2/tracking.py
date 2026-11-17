"""Fresh, bounded, exact-ID ERP purchase tracking. No mutation or local state rewrite."""
from datetime import datetime, timezone
from commerce_hub.adapters.erp import ERPError


def track_purchases(items, policy, reader, saved=(), *, discover=False):
    eligible = {item['entityKey']: item for item in items if policy.opening_binding(item) is not None}
    references = {}
    for item in eligible.values():
        for row in [*item.get('pendingPurchases', []), *item.get('formalPurchases', [])]:
            # Analysis includes same-SKU purchases from other warehouses as
            # context. Only the target warehouse supplies a tracking binding.
            if (row.get('warehouseMatch') is False
                    or row.get('warehouseName') is not None and row['warehouseName'] != item['warehouseName']):
                continue
            key = str(row['erpId'])
            references.setdefault(key, []).append((item, row))
    for row in saved:
        item = eligible.get(row.get('entityKey'))
        if item and row.get('erpId'):
            references.setdefault(str(row['erpId']), []).append((item, row))
    discovery_errors = []
    discovered_records = {}
    if discover:
        # Search only registered warehouses; never enumerate the shared tenant.
        # New IDs require exact SKU + product ID. Legacy IDs retain their existing
        # independent binding checks below, even when discovery is unavailable.
        for warehouse in sorted({item['warehouseName'] for item in eligible.values()}):
            members = [item for item in eligible.values() if item['warehouseName'] == warehouse]
            try:
                page = reader.read('/api/v1/purchase-orders', dict(warehouse_name=warehouse), page_size=50, max_pages=2)
                if not page.complete:
                    raise ERPError('PURCHASE_TRACKING_DISCOVERY_INCOMPLETE')
                if any(str(row.get('tenant_id')) != policy.source_tenant or row.get('warehouse_name') != warehouse for row in page.records):
                    raise ERPError('PURCHASE_TRACKING_RELATION_CHANGED')
                for row in page.records:
                    matched = False
                    for member in members:
                        if any(line.get('sku') == member['sku'] and str(line.get('product_id')) == str(member['productId']) for line in row.get('item_list', [])):
                            matched = True
                            key = str(row['id'])
                            if not any(m['entityKey'] == member['entityKey'] for m, _ in references.get(key, [])):
                                references.setdefault(key, []).append((member, dict(erpNumber=row['order_sn'], status=row.get('status_text'))))
                    if matched:
                        discovered_records[str(row['id'])] = row
            except (ERPError, OSError, ValueError, TypeError, KeyError) as exc:
                discovery_errors.append(dict(warehouseName=warehouse, code=exc.code if isinstance(exc, ERPError) else 'PURCHASE_TRACKING_DISCOVERY_UNAVAILABLE'))
    if len(references) > 50:
        raise ValueError('PURCHASE_TRACKING_SCOPE_LIMIT')
    result = []
    for key, sources in sorted(references.items()):
        item, previous = sources[0]
        view = dict(erpId=key, erpNumber=previous.get('erpNumber'),
            skus=sorted({m['sku'] for m, _ in sources}), warehouseName=item['warehouseName'],
            status=None, previousStatus=previous.get('status') or previous.get('erpStatus'),
            verifiedAt=None, verified=False, error=None, quantities=[])
        def apply_current(current):
            if (str(current.get('id')) != key or str(current.get('tenant_id')) != policy.source_tenant
                    or any(current.get('order_sn') != r.get('erpNumber') or current.get('warehouse_name') != m['warehouseName'] for m,r in sources)):
                raise ERPError('PURCHASE_TRACKING_RELATION_CHANGED')
            for member, _ in sources:
                lines = [line for line in current.get('item_list', []) if line.get('sku') == member['sku']]
                if not lines or any(line.get('product_id') is not None and str(line['product_id']) != str(member['productId']) for line in lines):
                    raise ERPError('PURCHASE_TRACKING_RELATION_CHANGED')
            status = current.get('status_text')
            if not isinstance(status, str) or not status:
                raise ERPError('PURCHASE_TRACKING_STATUS_MISSING')
            quantities = []
            for sku in view['skus']:
                for line in current['item_list']:
                    if line.get('sku') == sku:
                        quantities.append(dict(sku=sku, ordered=line.get('quantity'), received=line.get('received_qty'), pending=line.get('pending_qty')))
            view.update(status=status, verified=True, verifiedAt=datetime.now(timezone.utc).isoformat(),
                erpUpdatedAt=current.get('updated_at'), quantities=quantities,
                receivedQuantity=current.get('received_qty'), pendingQuantity=current.get('pending_qty'))
        try:
            raw = reader.detail('purchase-orders', key)
            current = raw.get('data', raw)
            apply_current(current)
        except (ERPError, OSError, ValueError, TypeError, KeyError) as exc:
            if isinstance(exc, ERPError) and exc.code == 'ERP_HTTP_ERROR' and exc.status == 404:
                fallback = discovered_records.get(key)
                if fallback is None:
                    view.update(status='ERP 已无此单', verified=True,
                        verifiedAt=datetime.now(timezone.utc).isoformat(), resolution='ERP_RECORD_NOT_FOUND')
                else:
                    try:
                        apply_current(fallback)
                    except (ERPError, ValueError, TypeError, KeyError) as fallback_error:
                        view['error'] = fallback_error.code if isinstance(fallback_error, ERPError) else 'PURCHASE_TRACKING_UNAVAILABLE'
            else:
                view['error'] = exc.code if isinstance(exc, ERPError) else 'PURCHASE_TRACKING_UNAVAILABLE'
        result.append(view)
    return dict(items=result, failedCount=sum(not r['verified'] for r in result),
        registeredSkuCount=len({item['sku'] for item in eligible.values()}), registeredScopeCount=len(eligible),
        discoveryErrors=discovery_errors, discoveryComplete=discover and not discovery_errors,
        checkedAt=datetime.now(timezone.utc).isoformat(), source='LIVE_ERP_EXACT_REGISTERED_IDS',
        coverage='当前登记商品已关联的采购单据；不等于 ERP 全量台账', businessWrites=0)
