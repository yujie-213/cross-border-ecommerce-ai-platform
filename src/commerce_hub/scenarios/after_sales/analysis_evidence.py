"""Evidence builders shared by admission and subsequent independent ERP refresh."""
from hashlib import sha256
from .common import require,redacted


def return_evidence(snapshot,return_id,sku):
    rows=[r for r in snapshot['items'] if r['id']==return_id and (not sku or r['sku']==sku)]
    require(len(rows)==1,'RETURN_ITEM_NOT_FOUND',404)
    item=rows[0];identity=dict(item['identity'],name=item['productName'])
    reason=redacted(item['reason']) or '未填写退货原因'
    facts=[dict(id='return-'+return_id+'-'+item['sku'],domain='RETURN',kind='OBSERVED',
        text=f"{item['state']} · {item['quantity']} 件 · {reason}",sourceRef=item['sourceRef'],observedAt=snapshot['observedAt']),
        dict(id='return-order-'+item['orderId'],domain='ORDER',kind='OBSERVED',
            text=f"订单 {item.get('orderNumber') or item['orderId']} · {item.get('orderDate') or '日期待核实'}",
            sourceRef='sales-orders:'+item['orderId'],observedAt=snapshot['observedAt'])]
    quality=[q for q in item.get('quality',[]) if q.get('sku')==item['sku']]
    if quality:
        facts.append(dict(id='return-quality-'+return_id+'-'+item['sku'],domain='RETURN_QUALITY',kind='OBSERVED',
            text='收货检查：'+ '；'.join(f"合格 {q['good_qty']} 件 / 异常 {q['bad_qty']} 件" for q in quality),
            value=quality,sourceRef=item['sourceRef'],observedAt=snapshot['observedAt']))
    return dict(snapshotRef=item['sourceRef'],facts=facts,missing=[],identityCandidates=[identity],identity=identity,
        latestUnverified=False,observedAt=snapshot['observedAt'],sourceNature='TEACHING_ERP_OBSERVED',
        sourceRef=dict(returnId=return_id,sku=item['sku'],sourceTenant=identity['sourceTenant'],storeId=identity['storeId']),
        customerText=reason,businessDate=item.get('createdAt'),title='退货调查 · '+item['productName'],
        platform=item.get('platform') or 'ERP',region=item.get('region') or 'UNKNOWN')


def monitor_evidence(result,sku,members):
    metric=next((r for r in result['monitor'] if r['sku']==sku),None)
    require(metric,'MONITOR_SKU_NOT_FOUND',404)
    candidates=[m for m in members if m.sku==sku and m.monitor.productId==metric['productId']]
    require(candidates,'MONITOR_SCOPE_NOT_FOUND',404)
    member=candidates[0]
    warehouse=member.sourceWarehouse if len({m.sourceWarehouse for m in candidates})==1 else 'UNKNOWN'
    identity=dict(sourceTenant=member.sourceTenant,productId=member.monitor.productId,sku=sku,name=metric['name'],
        category=metric.get('category','UNKNOWN'),attributes=metric.get('attributes',{}),storeId=member.sourceStore,
        warehouseId=warehouse,orderId='UNKNOWN',lineId='monitor:'+sku,source='OBSERVED')
    facts=[]
    for period,title in [('previous','上期'),('current','本期')]:
        rate=metric[period+'ReturnRate']
        text=f"{title}：已发货 {metric[period]} 件、实收退货 {metric[period+'Returns']} 件、退货率 {str(rate)+'%' if rate is not None else '无法计算'}、低星评价 {metric[period+'LowReviews']} 条"
        facts.append(dict(id='monitor-'+sku+'-'+period,domain='SKU_MONITOR',kind='DERIVED',text=text,
            sourceRef='monitor:'+sku+':'+metric[period+'Start'],observedAt=result['observedAt'],
            value={k:metric[k] for k in ('evidenceRefs','windowDays','endDate')}))
    for item in metric.get('evidenceItems',[]):
        ref=item['sourceRef']
        facts.append(dict(id='source-'+sha256((ref+':'+sku).encode()).hexdigest()[:20],domain=item['kind'],
            kind='OBSERVED',text=redacted(item['text']),sourceRef=ref,businessDate=item.get('businessDate'),observedAt=result['observedAt']))
    return dict(snapshotRef='monitor:'+sku+':'+result['window']['endDate'],facts=facts,
        missing=[] if result['complete'] else ['ERP数据未完整读取'],identityCandidates=[identity],identity=identity,
        latestUnverified=not result['complete'],observedAt=result['observedAt'],sourceNature='TEACHING_ERP_OBSERVED',
        sourceRef=dict(sku=sku,window=result['window']),businessDate=result['window']['endDate'],
        title='商品趋势调查 · '+metric['name'])
