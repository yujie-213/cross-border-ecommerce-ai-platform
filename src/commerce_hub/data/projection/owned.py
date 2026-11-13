"""D02: live owned facts and configurable SMA policy, feeding unchanged B01/B02."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from commerce_hub.data.contracts import AdmittedInput, fingerprint
from commerce_hub.data.admission import FieldProvenance

PROCUREMENT_RULE_VERSION = 's01-whole-carton-v1'


class OwnedInputError(ValueError):
    def __init__(self, code, path): self.code, self.path = code, path


def normalize_owned(captures, mapping, receipt, mapping_verified):
    m, b = mapping, mapping.monitor
    constraint_version = b.policy.version + '.whole-carton-v1'
    issues, assumptions = [], ['SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',
        'QUALITY_UNKNOWN_ADVISORY_ONLY', 'NO_ENTERPRISE_BUSINESS_ADMISSION',
        'REGISTERED_SUPPLY_ONLY_UNAPPROVED_PENDING_EXCLUDED',
        'HISTORICAL_STOCK_RECONSTRUCTED_IN_SIMULATION_NOT_BACKDATED_POSTING']
    assumptions.append('ERP_LEAD_DAYS_TO_ADVISORY_AVAILABLE_DATE_NOT_COMMITTED_PO_ETA')
    assumptions += ['OTHER_PROCUREMENT_CONDITIONS_UNCONFIRMED', 'D1_EXCLUDES_CURRENT_DAY_REMAINING_DEMAND']
    result = dict(input=None, issues=issues, ruleVersion=constraint_version, assumptions=assumptions)
    def block(code, path):
        issues.append(dict(code=code, severity='BLOCK', path=path, affects='CALCULATION', category='SOURCE_DATA'))
    def require(ok, code, path):
        if not ok: raise OwnedInputError(code, path)
    def rows(name): return captures.get(name, {}).get('rows', [])
    try:
        require(mapping_verified, 'IDENTITY_MAPPING_UNVERIFIED', 'mapping')
        for name, cap in captures.items():
            require(cap.get('complete') is True and not cap.get('error'), cap.get('error', 'SOURCE_COVERAGE_INCOMPLETE'), name)
        anchor = datetime.fromisoformat(receipt['completedAt'])
        zone = b.policy.timezone
        offset = timedelta(0) if zone == 'UTC' else timedelta(hours=int(zone[4:6]), minutes=int(zone[7:9])) * (-1 if zone[3] == '-' else 1)
        business_day = anchor.astimezone(timezone(offset)).date()
        start = business_day - timedelta(days=b.policy.observationDays)
        days = {start + timedelta(days=i): Decimal(0) for i in range(b.policy.observationDays)}
        products = rows('product')
        require(len(products) == 1 and str(products[0].get('id')) == b.productId
            and str(products[0].get('tenant_id')) == m.sourceTenant and products[0].get('sku') == m.sku,
            'PRODUCT_CONSTRAINT_RELATION_UNVERIFIED', 'product')
        product = products[0]
        require(product.get('unit') == 'piece', 'CARTON_UNIT_UNCONFIRMED', 'product/unit')
        carton = product.get('default_carton_qty')
        require(type(carton) is int and carton > 0, 'CARTON_QUANTITY_MISSING_OR_INVALID', 'product/default_carton_qty')
        multiple = Decimal(carton)
        require(len(rows('inventory')) == len(b.inventoryIds), 'INVENTORY_SET_CHANGED', 'inventory')
        require({str(r['id']) for r in rows('inventory')} == set(b.inventoryIds), 'INVENTORY_SET_CHANGED', 'inventory')
        inv = rows('inventory')
        require(all(str(r.get('product_id')) == b.productId and str(r.get('tenant_id')) == m.sourceTenant
            and str(r.get('store_id')) == m.sourceStore and str(r.get('wid')) == m.sourceWarehouse
            and r.get('sku') == m.sku for r in inv), 'INVENTORY_RELATION_DRIFT', 'inventory')
        available = sum(Decimal(str(r['available'])) for r in inv)
        physical = sum(Decimal(str(r['quantity'])) for r in inv)
        require(available >= 0 and physical == available, 'RESERVATION_OR_STOCK_SEMANTICS_UNCONFIRMED', 'inventory')
        supplier = rows('supplier')
        require(len(supplier) == 1 and str(supplier[0].get('id')) == b.supplierId
            and str(supplier[0].get('tenant_id')) == m.sourceTenant, 'SUPPLIER_RELATION_DRIFT', 'supplier')
        quotes = rows('quotes')
        require(len(quotes) == 1, 'QUOTE_AMBIGUOUS', 'quotes')
        quote = quotes[0]
        require(str(quote.get('id')) == b.quoteId and str(quote.get('product_id')) == b.productId
            and str(quote.get('supplier_id')) == b.supplierId and quote.get('sku') == m.sku
            and quote.get('quote_no') == b.quoteNo and quote.get('enabled') is True
            and quote.get('status') == 'effective'
            and quote['valid_from'] <= business_day.isoformat() <= quote['valid_to'], 'QUOTE_NOT_EFFECTIVE_OR_RELATED', 'quotes')
        moq, lead = Decimal(str(quote['minimum_quantity'])), quote['lead_days']
        require(moq > 0 and type(lead) is int and 0 <= lead <= 14, 'QUOTE_CONSTRAINT_INVALID', 'quotes')
        require(Decimal(quote['minimum_amount']) <= moq * Decimal(quote['unit_price']), 'MINIMUM_AMOUNT_NEEDS_RULE', 'quotes')
        sales = rows('sales')
        require({str(r['id']) for r in sales} == set(b.salesIds) and len(sales) == len(b.salesIds), 'REGISTERED_SALES_COVERAGE_INCOMPLETE', 'sales')
        total_sold, ledger_ids, chronological, history = Decimal(0), set(), [], []
        for sale in sales:
            require(str(sale.get('tenant_id')) == m.sourceTenant and sale.get('store_name') == m.storeName
                and sale.get('shipping_warehouse') == m.warehouseName, 'SALES_RELATION_DRIFT', 'sales')
            require(sale.get('payment_status') == '已支付' and sale.get('fulfillment_status') == '已发货'
                and sale.get('refund_status') == '无退款', 'SALES_NOT_NET_FULFILLED', 'sales')
            when = datetime.strptime(sale['order_time'], '%Y-%m-%d %H:%M:%S').date()
            require(when < business_day, 'INCOMPLETE_OR_FUTURE_BUSINESS_DAY', 'sales')
            items = [r for r in sale['item_list'] if r.get('sku') == m.sku]
            require(len(items) == 1, 'SALES_ITEM_AMBIGUOUS', 'sales')
            qty = Decimal(str(items[0]['quantity']))
            require(qty > 0 and qty == qty.to_integral_value(), 'SALES_QUANTITY_INVALID', 'sales')
            wf = rows('workflow-' + str(sale['id']))
            workflow = wf[0].get('data', {}) if len(wf) == 1 else {}
            require(workflow.get('local_only') is True and workflow.get('state') == 'shipped'
                and workflow.get('order_id') == sale['id'] and len(workflow.get('shipments', [])) >= 1,
                'FULFILLMENT_NOT_VERIFIED', 'sales')
            posted = Decimal(0)
            for shipment in workflow['shipments']:
                require(shipment.get('order_id') == sale['id'], 'SHIPMENT_PARENT_DRIFT', 'sales')
                ledgers = rows('ledger-' + str(shipment['outbound_id']))
                own = [r for r in ledgers if r.get('sku') == m.sku]
                require(bool(own), 'OUTBOUND_LEDGER_MISSING', 'sales')
                for row in own:
                    require(row['id'] not in ledger_ids and row.get('resource') == 'outbound-orders'
                        and row.get('record_id') == shipment['outbound_id'] and row.get('warehouse_name') == m.warehouseName
                        and str(row.get('inventory_id')) in b.inventoryIds and row.get('operation') == 'post'
                        and not row.get('reverses_id'), 'DUPLICATE_OR_FOREIGN_LEDGER', 'sales')
                    delta = Decimal(str(row['delta_quantity']))
                    require(delta < 0 and Decimal(str(row['delta_available'])) == delta
                        and Decimal(str(row['after_quantity'])) - Decimal(str(row['before_quantity'])) == delta
                        and Decimal(str(row['after_available'])) - Decimal(str(row['before_available'])) == delta,
                        'LEDGER_ARITHMETIC_MISMATCH', 'sales')
                    ledger_ids.add(row['id']); posted -= delta
                    chronological.append((row['created_at'], row['id'], row))
            require(posted == qty, 'FULFILLMENT_LEDGER_QUANTITY_MISMATCH', 'sales')
            total_sold += qty
            if when in days: days[when] += qty
            history.append(dict(businessDate=when.isoformat(), quantity=str(qty),
                orderRef='erp-order-' + str(sale['id']), createdAt=sale['created_at'], postedAt=workflow.get('shipped_at')))
        # No unexplained movements or missing registered orders; historical seed
        # is simulation provenance, never a claim that ERP posted it in the past.
        require(Decimal(b.openingQuantity) - total_sold == physical, 'STOCK_SALES_RECONCILIATION_FAILED', 'inventory')
        running = Decimal(b.openingQuantity)
        for _, _, row in sorted(chronological):
            require(Decimal(str(row['before_quantity'])) == running, 'UNEXPLAINED_STOCK_MOVEMENT', 'inventory')
            running += Decimal(str(row['delta_quantity']))
            require(running > 0, 'HISTORICAL_STOCKOUT_DEMAND_CENSORED', 'demand')
        require(running == physical, 'STOCK_LEDGER_RECONCILIATION_FAILED', 'inventory')
        supply, excluded = [], []
        require({str(r['id']) for r in rows('purchases')} == set(b.purchaseIds), 'PURCHASE_SET_CHANGED', 'purchases')
        for purchase in rows('purchases'):
            require(str(purchase.get('tenant_id')) == m.sourceTenant and purchase.get('warehouse_name') == m.warehouseName
                and str(purchase.get('supplier_id')) == b.supplierId
                and any(x.get('sku') == m.sku for x in purchase.get('item_list', [])), 'PURCHASE_RELATION_DRIFT', 'purchases')
            # Do not promote pending_qty to effective supply from quantity alone.
            require(purchase.get('status_text') in {'待审核', '待提交', '草稿', '未提交', '已取消'},
                'EFFECTIVE_SUPPLY_REQUIRES_APPROVED_ETA_MAPPING', 'purchases')
            excluded.append(dict(orderRef='erp-purchase-' + str(purchase['id']), status=purchase['status_text'],
                pendingQuantity=str(purchase.get('pending_qty')), reason='NOT_APPROVED_EFFECTIVE_SUPPLY'))
        average = sum(days.values()) / Decimal(b.policy.observationDays)
        horizon = lead + b.policy.coverageDays
        require(1 <= horizon <= 31, 'FORECAST_HORIZON_UNSUPPORTED', 'policy')
        # B01 input precision is 8 decimals; document conservative upward rounding.
        daily = average.quantize(Decimal('.00000001'), rounding=ROUND_CEILING)
        canonical = dict(sku=m.scope['canonicalSkuIds'][0], store=m.scope['storeIds'][0], warehouse=m.scope['warehouseIds'][0])
        value = AdmittedInput(sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',
            fixtureId='owned-' + receipt['acquisitionId'], provenanceRef='owned-' + fingerprint(receipt)[:32],
            rulesRef=constraint_version, asOf=anchor, businessDate=business_day, coverageComplete=True,
            mapping=dict(version=m.version, sourceSku=canonical['sku'], sourceStore=canonical['store'],
                sourceWarehouse=canonical['warehouse'], canonicalSkuId=canonical['sku'], storeId=canonical['store'],
                warehouseId=canonical['warehouse'], sourceUnit='EA', unit='EA', unitsPerSourceUnit='1'),
            inventory=[dict(recordId='owned-stock-' + fingerprint(b.inventoryIds)[:24], **canonical,
                unit='EA', availableQty=str(available), reservedQty=None, semantics='NET_AVAILABLE', sourceUpdatedAt=anchor)],
            demand=[dict(recordId=f'owned-demand-{i}', **canonical, unit='EA', day=business_day + timedelta(days=i),
                quantity=str(daily), semantics='INCREMENTAL_EXCLUDES_RESERVED') for i in range(1, horizon + 1)],
            supply=supply, policy=dict(version=constraint_version, horizonDays=horizon, bufferDays=0, maxAgeHours=24,
                moq=str(moq), orderMultiple=str(multiple), candidateDates=[business_day + timedelta(days=max(1, lead))],
                maxOrderQty=str(((daily * horizon + moq) / multiple).to_integral_value(rounding=ROUND_CEILING) * multiple),
                otherConstraints='UNCONFIRMED', qualityDisposition='UNKNOWN', advisoryOnly=True))
        forecast = dict(method='SIMPLE_MOVING_AVERAGE', policyVersion=b.policy.version,
            timezone=b.policy.timezone, observationDays=b.policy.observationDays,
            windowStart=start.isoformat(), windowEnd=(business_day - timedelta(days=1)).isoformat(),
            dailySales=[dict(day=d.isoformat(), quantity=str(q)) for d, q in sorted(days.items())],
            totalSales=str(sum(days.values())), averageDailyDemand=str(average), calculationDailyDemand=str(daily),
            forecastDays=b.policy.forecastDays, forecastQuantity=str(average * b.policy.forecastDays),
            calculationHorizonDays=horizon, leadDays=lead, coverageDays=b.policy.coverageDays,
            rounding='DAILY_CEILING_8_DECIMALS', history=history,
            constraints=dict(moq=str(moq), supplierLeadDays=lead, quoteVersion=quote['version'],
                orderMultiple=str(multiple), defaultCartonQty=str(multiple), wholeCartonRequired=True,
                ruleVersion=PROCUREMENT_RULE_VERSION, quantityResolution='1', quality='UNKNOWN', procurementEligible=False,
                moqSource='supplier-quotes.minimum_quantity', orderMultipleSource='products.default_carton_qty',
                otherConditions='UNCONFIRMED', availableDateBasis='QUOTE_LEAD_NOT_COMMITTED_SELLABLE_ETA'),
            excludedSupply=excluded, stockReconciliation=dict(openingQuantity=b.openingQuantity,
                fulfilledQuantity=str(total_sold), availableQuantity=str(available), status='PASS'))
        provenance = []
        for path, nature, val, source in [('/inventory', 'ERP_NETWORK', str(available), 'inventory'),
            ('/history', 'ERP_NETWORK', forecast['dailySales'], 'sales'),
            ('/policy/moq', 'ERP_NETWORK', str(moq), 'quotes'),
            ('/policy/leadDays', 'ERP_NETWORK', lead, 'quotes'),
            ('/forecast', 'CONTROLLED_FACT', forecast['forecastQuantity'], 'sales'),
            ('/policy/orderMultiple', 'ERP_NETWORK', str(multiple), 'product'),
            ('/policy/wholeCartonRule', 'CONTROLLED_FACT', PROCUREMENT_RULE_VERSION, 'product')]:
            provenance.append(FieldProvenance(fieldPath=path, assertion='RULE_VALUE' if nature != 'ERP_NETWORK' else 'VALUE_OBSERVED',
                nature=nature, sourceVersion=PROCUREMENT_RULE_VERSION if path in {'/policy/orderMultiple', '/policy/wholeCartonRule'} else b.policy.version, owner='project-owner',
                sourceRef='snapshot:' + receipt['acquisitionId'] + '/' + source, observedAt=anchor,
                valueDigest=fingerprint(val), factBasis=(
                    'Owner confirmed MOQ and mandatory whole-carton procurement; registered product default_carton_qty is the order multiple for the related supplier quote'
                    if path == '/policy/wholeCartonRule' else 'Owner approved configurable SMA from independently read ERP business dates'
                    ) if nature == 'CONTROLLED_FACT' else None).model_dump(mode='json'))
        result.update(input=value.model_dump(mode='json'), forecast=forecast, fieldProvenance=provenance)
        issues.append(dict(code='OTHER_PROCUREMENT_CONDITIONS_UNCONFIRMED', severity='WARN', path='policy/otherConstraints', affects='CANDIDATES', category='BUSINESS_RULE'))
    except OwnedInputError as error:
        block(error.code, error.path)
    except (ValueError, KeyError, TypeError, ArithmeticError):
        block('OWNED_SOURCE_FIELDS_INVALID', 'input')
    return result
