"""Conservative formal-purchase adapter; never derives sellable ETA from lead days."""
from decimal import Decimal, InvalidOperation

POLICY = 's01-approved-purchases-v1'
# Local compatibility contract: 1 reviewed/pending order, 2 ordered/pending arrival.
# These are contract mappings, not a claim of positive live workflow verification.
FORMAL_STATES = ('待下单', '待到货', '部分到货')


def integer(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
        return int(number) if number.is_finite() and 0 <= number <= 10**9 and number == number.to_integral_value() else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def project_purchases(rows, mapping, proofs):
    """Only independently verified operation relations establish store/purpose.

    Header pending/received totals cannot be assigned to one SKU on multi-line POs.
    Current ERP lacks confirmed sellable-time/closure semantics: display only.
    """
    items, unresolved = [], 0
    seen = set()
    for row in rows:
        if (row.get('status_text') not in FORMAL_STATES or str(row.get('tenant_id')) != mapping.sourceTenant
                or row.get('warehouse_name') != mapping.warehouseName or row.get('id') in seen):
            raise ValueError('FORMAL_PURCHASE_SOURCE_DRIFT')
        seen.add(row['id'])
        lines = row.get('item_list')
        if not isinstance(lines, list) or not lines or any(not isinstance(line, dict) or not line.get('sku') for line in lines):
            raise ValueError('FORMAL_PURCHASE_LINES_INCOMPLETE')
        own = [(i, line) for i, line in enumerate(lines) if line['sku'] == mapping.sku]
        if not own:
            continue
        proof = next((p for p in proofs if str(row['id']) == p.get('erpId') and row.get('order_sn') == p.get('erpNumber')
            and p.get('scope') == mapping.scope and p.get('datasetId') == mapping.monitor.datasetId
            and p.get('purpose') == 'SALES_REPLENISHMENT'), None)
        if proof is None:
            unresolved += 1
            continue
        for index, line in own:
            ordered = integer(line.get('quantity'))
            received = integer(line.get('received_qty'))
            # Only a single SKU line may use header receipt counters for display.
            if len(lines) == 1 and received is None:
                received = integer(row.get('received_qty'))
            remaining = ordered - received if ordered is not None and received is not None and received <= ordered else None
            items.append(dict(erpId=str(row['id']), erpNumber=row['order_sn'], lineIndex=index, sku=mapping.sku,
                status=row['status_text'], orderedQuantity=str(ordered) if ordered is not None else None,
                receivedQuantity=str(received) if received is not None else None,
                unreceivedQuantity=str(remaining) if remaining is not None else None,
                effectiveSupplyQuantity=None, plannedArrival=row.get('planned_arrival'), sellableDate=None,
                includedInCalculation=False, reason='SELLABLE_DATE_AND_CLOSURE_UNCONFIRMED',
                scopeBasis='INDEPENDENTLY_READBACK_VERIFIED_REQUISITION', purpose='SALES_REPLENISHMENT'))
    return dict(policyVersion=POLICY, coverage='COMPLETE_FILTERED_FORMAL_STATES', items=items,
        unresolvedScopeCount=unresolved, effectiveSupplyStatus='UNCONFIRMED' if items or unresolved else 'NO_MATCHING_FORMAL_PURCHASE',
        limitations=['ERP_PLANNED_ARRIVAL_IS_NOT_SELLABLE_DATE', 'UNCONFIRMED_SUPPLY_NOT_DEDUCTED',
                      'OTHER_FORMAL_STATE_LABELS_REQUIRE_CONTRACT_VERIFICATION'])
