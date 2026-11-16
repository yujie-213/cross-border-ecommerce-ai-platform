"""B01 quantity-return-rate-v1. Integer cross products determine anomalies."""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from commerce_hub.scenarios.after_sales.common import digest, timestamp, require

DEFAULT_RULE = dict(version='return-quantity-v1', observationDays=30, minOrders=20,
    minQuantity=20, deltaBasisPoints=1000, minReceived=3)


def validate_records(records, manifest):
    """Fail closed on identity, causal/time and quantity ambiguity; never drop bad rows."""
    require(manifest.get('sourceNature') == 'MIDDLEWARE_TEACHING_DATA', 'SOURCE_MIXED')
    require(manifest.get('timezone') == 'Asia/Shanghai', 'TIMEZONE_UNKNOWN')
    require(manifest.get('coverageComplete') is True, 'COVERAGE_INCOMPLETE')
    require(len(records) <= 10000, 'DATASET_LIMIT')
    seen, by_type = {}, defaultdict(list)
    for r in records:
        require(isinstance(r, dict) and r.get('type') in {'product', 'order', 'line', 'shipment', 'return', 'feedback'}, 'RECORD_INVALID')
        require(r.get('sourceNature') == manifest['sourceNature'] and r.get('sourceTenant') == manifest['sourceTenant'], 'SOURCE_MIXED')
        require(isinstance(r.get('id'), str) and 0 < len(r['id']) <= 64 and 'teacher' not in r, 'RECORD_INVALID')
        key = (r['type'], r['id'])
        require(key not in seen or seen[key] == digest(r), 'DUPLICATE_CONFLICT')
        if key in seen:
            continue
        seen[key] = digest(r); by_type[r['type']].append(r)
    products = {r['id']: r for r in by_type['product']}
    orders = {r['id']: r for r in by_type['order']}
    lines = {r['id']: r for r in by_type['line']}
    require(products and orders and lines, 'POPULATION_MISSING')
    for p in products.values():
        require(all(isinstance(p.get(k),str) and p[k] for k in ('sku','name','category')) and p['category'] in {'APPAREL','ELECTRONICS'} and isinstance(p.get('attributes'),dict),'PRODUCT_ATTRIBUTES_INVALID')
    for o in orders.values():
        require(isinstance(o.get('storeId'),str) and o['storeId'],'IDENTITY_UNRESOLVED')
        timestamp(o.get('paidAt'))
    require(set(manifest['population']) == set(lines) and len(manifest['population']) == len(lines), 'POPULATION_INCOMPLETE')
    require(manifest['counts'] == {k: len(v) for k, v in by_type.items()}, 'COUNT_MISMATCH')
    identity = {}
    for line in lines.values():
        require(line.get('productId') in products and line.get('orderId') in orders, 'IDENTITY_UNRESOLVED')
        p, o = products[line['productId']], orders[line['orderId']]
        require(line.get('sku') == p['sku'] and line.get('storeId') == o['storeId']
            and line.get('warehouseId') in manifest['warehouseIds'], 'IDENTITY_UNRESOLVED')
        require(type(line.get('quantity')) is int and line['quantity'] > 0, 'QUANTITY_INVALID')
        identity[line['id']] = line
    shipped, stages, order_skus = defaultdict(int), {}, defaultdict(list)
    batches={};unique_shipments=[]
    for shipment in by_type['shipment']:
        require(shipment.get('lineId') in lines and type(shipment.get('quantity')) is int and shipment['quantity'] > 0, 'SHIPMENT_INVALID')
        timestamp(shipment.get('at'))
        require(isinstance(shipment.get('batchId'),str) and shipment['batchId'],'BATCH_ID_MISSING')
        batch_key=(shipment['batchId'],shipment['lineId'])
        batch_value={k:v for k,v in shipment.items() if k!='id'}
        require(batch_key not in batches or batches[batch_key]==batch_value,'DUPLICATE_BATCH_CONFLICT')
        if batch_key in batches:continue
        batches[batch_key]=batch_value;unique_shipments.append(shipment)
        shipped[shipment['lineId']] += shipment['quantity']
    by_type['shipment']=unique_shipments
    for line in lines.values():
        require(shipped[line['id']] <= line['quantity'], 'SHIPMENT_EXCEEDS_ORDER')
        if line.get('fulfillmentComplete') is True:
            require(shipped[line['id']] == line['quantity'], 'FULFILLMENT_INCOMPLETE')
        order_skus[(line['orderId'], line['productId'])].append(line)
    for event in sorted(by_type['return'], key=lambda r: timestamp(r.get('at'))):
        require(event.get('lineId') in lines and event.get('stage') in {'draft','requested','authorized','received','refunded','cancelled'}, 'RETURN_INVALID')
        require(type(event.get('quantity')) is int and 0 < event['quantity'] <= shipped[event['lineId']], 'RETURN_EXCEEDS_SHIPMENT')
        key = (event.get('returnId'), event['lineId'])
        require(event.get('returnId'), 'RETURN_ID_MISSING')
        previous = stages.get(key)
        allowed = {None: {'draft','requested'}, 'draft': {'requested','cancelled'}, 'requested': {'authorized','cancelled'},
            'authorized': {'received','cancelled'}, 'received': {'refunded'}, 'refunded': set(), 'cancelled': set()}
        require(event['stage'] in allowed[previous['stage'] if previous else None], 'RETURN_CAUSAL_CONFLICT')
        require(not previous or previous['quantity'] == event['quantity'], 'RETURN_QUANTITY_CONFLICT')
        stages[key] = event
        if event['stage'] == 'refunded':
            try:amount=Decimal(str(event.get('amount')))
            except InvalidOperation:amount=Decimal('NaN')
            require(isinstance(event.get('currency'),str) and len(event['currency'])==3 and amount.is_finite() and amount>=0,'REFUND_ALLOCATION_MISSING')
    received = defaultdict(int)
    for event in by_type['return']:
        if event['stage'] == 'received': received[event['lineId']] += event['quantity']
    require(all(n <= shipped[lid] for lid,n in received.items()), 'RETURN_EXCEEDS_SHIPMENT')
    for f in by_type['feedback']:
        require(f.get('orderId') in orders and (not f.get('lineId') or f['lineId'] in lines and lines[f['lineId']]['orderId'] == f['orderId']), 'FEEDBACK_IDENTITY_INVALID')
        require(isinstance(f.get('text'), str) and 0 < len(f['text']) <= 6000, 'FEEDBACK_INVALID')
        timestamp(f.get('at'))
    return by_type


def analyze(records, manifest, windows, as_of, rule=None):
    rule = dict(rule or DEFAULT_RULE)
    require(set(rule) == set(DEFAULT_RULE) and isinstance(rule['version'], str), 'RULE_INVALID')
    require(all(type(rule[k]) is int and rule[k] > 0 for k in DEFAULT_RULE if k != 'version')
        and rule['observationDays'] <= 365 and rule['deltaBasisPoints'] <= 10000, 'RULE_INVALID')
    data = validate_records(records, manifest)
    require(len(windows) == 2 and all(len(w) == 2 for w in windows), 'WINDOW_INVALID')
    bounds = [(timestamp(s), timestamp(e)) for s,e in windows]
    require(bounds[0][0] < bounds[0][1] <= bounds[1][0] < bounds[1][1]
        and bounds[0][1]-bounds[0][0] == bounds[1][1]-bounds[1][0], 'WINDOW_INVALID')
    end = timestamp(as_of); duration = timedelta(days=rule['observationDays'])
    require(timestamp(manifest['coverageThrough']) >= end, 'COVERAGE_INCOMPLETE')
    shipments = defaultdict(list)
    for s in data['shipment']: shipments[s['lineId']].append(s)
    grouped = defaultdict(list)
    for l in data['line']:
        grouped[(l['productId'], l['sku'], l['storeId'], l['orderId'])].append(l)
    populations = defaultdict(lambda: [[], []])
    for (pid, sku, store, oid), lines in grouped.items():
        batches = [s for l in lines for s in shipments[l['id']]]
        if not batches:
            # Without t0 the fixed population cannot be assigned safely to a window.
            for bucket in populations[(pid,sku,store)]: bucket.append(dict(unknown='SHIPMENT_MISSING', orderId=oid))
            continue
        t0 = max(timestamp(s['at']) for s in batches)
        for i,(start,stop) in enumerate(bounds):
            if start <= t0 < stop:
                populations[(pid,sku,store)][i].append(dict(lines=lines, batches=batches,t0=t0,orderId=oid))
    results = []
    for p in data['product']:
        stores = sorted({l['storeId'] for l in data['line'] if l['productId'] == p['id']})
        for store in stores:
            groups = []
            for items in populations[(p['id'],p['sku'],store)]:
                n=d=mature=0; issues=[]; stage_counts=defaultdict(int); money=defaultdict(Decimal); refs=[]; outside=[]
                for item in items:
                    if 'unknown' in item: issues.append(item['unknown']); continue
                    d += sum(s['quantity'] for s in item['batches'])
                    refs.extend(s['id'] for s in item['batches'])
                    if not all(l.get('fulfillmentComplete') is True for l in item['lines']): issues.append('FULFILLMENT_INCOMPLETE')
                    if end < item['t0'] + duration: issues.append('IMMATURE_COHORT')
                    else: mature += 1
                    lids = {l['id'] for l in item['lines']}; stage_ids=set();latest={};authorized_in_window=set()
                    for event in data['return']:
                        if event['lineId'] not in lids or timestamp(event['at']) > end: continue
                        latest_key=(event['returnId'],event['lineId'])
                        if latest_key not in latest or timestamp(event['at'])>timestamp(latest[latest_key]['at']):latest[latest_key]=event
                        if not item['t0'] <= timestamp(event['at']) < item['t0']+duration:
                            outside.append(event['id']); continue
                        refs.append(event['id'])
                        if event['stage']=='authorized':authorized_in_window.add(latest_key)
                        if (event['returnId'],event['lineId'],event['stage']) not in stage_ids:
                            stage_counts[event['stage']] += event['quantity'];stage_ids.add((event['returnId'],event['lineId'],event['stage']))
                        if event['stage']=='received': n += event['quantity']
                        if event['stage']=='refunded': money[event['currency']] += Decimal(str(event['amount']))
                    stage_counts['authorizedValid']+=sum(e['quantity'] for key,e in latest.items() if key in authorized_in_window and e['stage'] in {'authorized','received','refunded'})
                if mature < rule['minOrders'] or d < rule['minQuantity']: issues.append('INSUFFICIENT_SAMPLE')
                if not d: issues.append('DENOMINATOR_MISSING')
                groups.append(dict(numerator=n,denominator=d,orders=len(items),matureOrders=mature,
                    ratePercent=str((Decimal(n)*100/Decimal(d)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)) if d and not issues else None,
                    status='UNKNOWN' if issues else 'KNOWN',unresolved=sorted(set(issues)),stages=dict(stage_counts),
                    refundAmounts={k:str(v) for k,v in money.items()},evidenceRefs=refs,outsideWindow=outside))
            old,new=groups
            known=all(g['status']=='KNOWN' for g in groups)
            anomaly = known and (new['numerator']*old['denominator']-old['numerator']*new['denominator'])*10000 >= rule['deltaBasisPoints']*new['denominator']*old['denominator'] and new['numerator']>=rule['minReceived']
            delta = (Decimal(new['numerator'])*100/new['denominator']-Decimal(old['numerator'])*100/old['denominator']) if known else None
            results.append(dict(productId=p['id'],sku=p['sku'],name=p['name'],storeId=store,groups=groups,
                deltaPercentagePoints=str(delta.quantize(Decimal('.01'))) if delta is not None else None,
                finding='NEEDS_INVESTIGATION' if anomaly else 'NO_THRESHOLD_SIGNAL' if known else 'UNKNOWN'))
    return dict(metricVersion='return-quantity-v1',rule=rule,windows=windows,asOf=as_of,items=results,
        definition='完成订单商品的观察窗内实收件数 / 唯一实际发货件数；不代表已确认质量缺陷')
