"""D02 observed sales estimator. No purchasing fields, invented zeroes or ERP rates."""
from collections import defaultdict, Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from commerce_hub.data.contracts import fingerprint

VERSION='s01-product-demand-v1'


def sales_reference(catalog,entity):
    today=date.fromisoformat(catalog['businessDate'])
    days=defaultdict(Decimal);accepted=[];excluded=Counter();seen={};numbers={};conflict=False
    stores=[s for s in catalog['stores']['rows'] if s.get('store_name')==entity.get('storeName')]
    warehouses=[w for w in catalog['warehouses']['rows'] if w.get('name')==entity.get('warehouseName')]
    products=[p for p in catalog['products']['rows'] if str(p['id'])==entity.get('productId') and p.get('sku')==entity.get('sku')]
    if (len(products)!=1 or len(stores)!=1 or len(warehouses)!=1
        or str(stores[0]['id'])!=entity.get('storeId') or str(warehouses[0]['id'])!=entity.get('warehouseId')
        or any(not catalog[n]['complete'] for n in ['products','stores','warehouses'])):
        return dict(available=False,reason='SALES_SCOPE_UNRESOLVED',history=[],excluded={})
    for sale in catalog['sales']['rows']:
        if sale.get('store_name')!=entity['storeName'] or sale.get('shipping_warehouse')!=entity['warehouseName']:continue
        lines=[l for l in sale.get('item_list',[]) if l.get('sku')==entity['sku']]
        if not lines:continue
        if str(sale.get('tenant_id'))!=entity['sourceTenant']:
            excluded['FOREIGN_SALES_RECORD']+=1;conflict=True;continue
        # Explicit source values only. Null refund state is not proof of no refund.
        if (sale.get('payment_status') not in {'已支付','Paid'} or sale.get('fulfillment_status') not in {'已发货','Shipped'}
            or sale.get('refund_status') not in {'无退款','无','None','No refund'}
            or sale.get('status_text') in {'已取消','取消','Cancelled','Canceled'}):
            excluded['SALES_NOT_NET_FULFILLED']+=1;continue
        try:
            from commerce_hub.data.projection.runtime import business_date
            timestamp=datetime.fromisoformat(str(sale['order_time']).replace('Z','+00:00'))
            when=business_date(timestamp.isoformat(),catalog.get('timeBasis',{}).get('timezone','UTC+08:00')) if timestamp.tzinfo else timestamp.date()
            if when>=today:excluded['INCOMPLETE_OR_FUTURE_BUSINESS_DAY']+=1;continue
            if len(lines)!=1:raise ValueError()
            line=lines[0]
            if line.get('product_id') is not None and str(line['product_id'])!=entity['productId']:raise ValueError()
            if isinstance(line.get('quantity'),bool):raise ValueError()
            qty=Decimal(str(line['quantity']))
            if not qty.is_finite() or qty<=0 or qty!=qty.to_integral_value() or qty>100000000:raise ValueError()
            if sale.get('id') is None:raise ValueError()
        except (ValueError,KeyError,InvalidOperation,TypeError):excluded['SALES_FIELDS_INVALID']+=1;continue
        key=str(sale['id']);value=(when,str(qty))
        if key in seen:
            excluded['DUPLICATE_SALES_RECORD']+=1
            if seen[key]!=value:conflict=True
            continue
        number=sale.get('order_sn')
        if number and number in numbers:
            excluded['DUPLICATE_SALES_NUMBER']+=1
            if numbers[number]!=value:conflict=True
            continue
        seen[key]=value
        if number:numbers[number]=value
        days[when]+=qty;accepted.append(dict(orderRef='erp-order-'+key,businessDate=when.isoformat(),quantity=str(qty)))
    if not days:return dict(available=False,reason='NO_TRUSTED_SALES_SAMPLES',history=[],excluded=dict(excluded))
    first,last=min(days),max(days);span=(last-first).days+1;total=sum(days.values());active=len(days)
    rate=total/Decimal(span);upper=total/Decimal(active);age=(today-last).days
    risks=[]
    if span>active:risks.append('HISTORY_DATES_WITHOUT_RECORDS_UNKNOWN')
    if age>7:risks.append('STALE_SALES_SAMPLES')
    if active<3:risks.append('LOW_SALES_SAMPLE')
    if not catalog['sales']['complete']:risks.append('SALES_ENUMERATION_INCOMPLETE')
    if conflict:risks.append('CONFLICTING_SALES_RECORDS')
    if max(days.values())/total>Decimal('.5'):risks.append('SALES_CONCENTRATED_IN_ONE_DAY')
    confidence='LOW' if risks else 'MEDIUM'
    return dict(available=not conflict,reason='CONFLICTING_SALES_RECORDS' if conflict else None,method='OBSERVED_INTERVAL_REFERENCE',
        policyVersion=VERSION,sampleStart=first.isoformat(),sampleEnd=last.isoformat(),sampleAgeDays=age,
        observedDays=active,spanDays=span,unknownDays=span-active,orderCount=len(accepted),totalSales=str(total),
        averageDailyDemand=str(rate),salesRecordDayAverage=str(upper),confidence=confidence,risks=risks,
        history=accepted,excluded=dict(excluded),dailySales=[dict(day=d.isoformat(),quantity=str(q)) for d,q in sorted(days.items())],
        sampleDigest=fingerprint(accepted),sourceEnumerationComplete=catalog['sales']['complete'],
        denominator='FIRST_TO_LAST_OBSERVED_DATE_INCLUSIVE',
        assumption='区间参考以首末记录之间未记录日期无额外需求作保守试算，不声明这些日期实际销量为零；记录日均作为另一情景。')
