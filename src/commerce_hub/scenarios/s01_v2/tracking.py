"""Fresh, bounded, exact-ID ERP purchase tracking. No mutation or local state rewrite."""
from datetime import datetime, timezone
from commerce_hub.adapters.erp import ERPError


def track_purchases(items, policy, reader, saved=()):
    eligible = {item['entityKey']: item for item in items if policy.opening_binding(item) is not None}
    references = {}
    for item in eligible.values():
        for row in [*item.get('pendingPurchases', []), *item.get('formalPurchases', [])]:
            key = str(row['erpId'])
            references.setdefault(key, []).append((item, row))
    for row in saved:
        item = eligible.get(row.get('entityKey'))
        if item and row.get('erpId'):
            references.setdefault(str(row['erpId']), []).append((item, row))
    if len(references) > 50:
        raise ValueError('PURCHASE_TRACKING_SCOPE_LIMIT')
    result = []
    for key, sources in sorted(references.items()):
        item, previous = sources[0]
        view = dict(erpId=key, erpNumber=previous.get('erpNumber'),
            skus=sorted({m['sku'] for m, _ in sources}), warehouseName=item['warehouseName'],
            status=None, previousStatus=previous.get('status') or previous.get('erpStatus'),
            verifiedAt=None, verified=False, error=None, quantities=[])
        try:
            raw = reader.detail('purchase-orders', key)
            current = raw.get('data', raw)
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
        except (ERPError, OSError, ValueError, TypeError, KeyError) as exc:
            view['error'] = exc.code if isinstance(exc, ERPError) else 'PURCHASE_TRACKING_UNAVAILABLE'
        result.append(view)
    return dict(items=result, failedCount=sum(not r['verified'] for r in result),
        checkedAt=datetime.now(timezone.utc).isoformat(), source='LIVE_ERP_EXACT_REGISTERED_IDS',
        coverage='当前登记商品已关联的采购单据；不等于 ERP 全量台账', businessWrites=0)
