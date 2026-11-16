"""Independent teaching transactions; never ERP-native and no teacher answers in payload."""
from collections import Counter
from datetime import datetime, timedelta, timezone

from .common import SOURCE, SOURCE_TENANT, digest


def golden_package():
    records = []
    def add(kind, rid, **kw):
        records.append(dict(type=kind,id=rid,sourceNature=SOURCE,sourceTenant=SOURCE_TENANT,**kw))
    add('product','b-shirt',sku='B-TEACH-SHIRT',name='教学纯棉上衣',category='APPAREL',attributes={'size':'M','material':'cotton'})
    add('product','b-cable',sku='B-TEACH-CABLE',name='教学USB充电线',category='ELECTRONICS',attributes={'connector':'USB-C','ratedPower':'60W'})
    starts = [datetime(2026,8,1,tzinfo=timezone.utc), datetime(2026,9,1,tzinfo=timezone.utc)]
    for period,start in enumerate(starts):
        for i in range(20):
            oid=f'b-order-{period}-{i:02}'
            at=start+timedelta(hours=i*12)
            add('order',oid,storeId='b-teaching-store',orderNumber=oid,paid=True,paidAt=at.isoformat())
            for product,sku in [('b-shirt','B-TEACH-SHIRT'),('b-cable','B-TEACH-CABLE')]:
                lid=f'{oid}-{product}'
                add('line',lid,orderId=oid,productId=product,sku=sku,storeId='b-teaching-store',warehouseId='b-teaching-warehouse',quantity=2,fulfillmentComplete=True)
                add('shipment',f'ship-{lid}',lineId=lid,quantity=2,at=at.isoformat(),batchId=f'batch-{lid}')
                # One received per period for cable; shirt grows from 1 to 12 units.
                has_return=i < (6 if period==1 and product=='b-shirt' else 1)
                quantity=2 if period==1 and product=='b-shirt' else 1
                if has_return:
                    for stage,days in [('requested',2),('authorized',3),('received',5),('refunded',7)]:
                        add('return',f'{stage}-{lid}',returnId=f'return-{lid}',lineId=lid,stage=stage,quantity=quantity,
                            at=(at+timedelta(days=days)).isoformat(),**(dict(currency='CNY',amount=str(quantity*20)) if stage=='refunded' else {}))
                    text='穿着尺寸偏小，与商品说明不一致。' if product=='b-shirt' else '连接设备时偶尔断开，需要核对接口兼容。'
                    add('feedback',f'feedback-{lid}',orderId=oid,lineId=lid,text=text,language='zh',at=(at+timedelta(days=6)).isoformat(),channel='ORDER_FEEDBACK')
    counts=dict(Counter(r['type'] for r in records))
    blocks=[records[i:i+60] for i in range(0,len(records),60)]
    manifest=dict(schemaVersion='1.0.0',datasetId='b-golden-20261116',version='v1',sourceNature=SOURCE,sourceTenant=SOURCE_TENANT,
        timezone='Asia/Shanghai',coverageComplete=True,coverageThrough='2026-11-01T00:00:00Z',
        warehouseIds=['b-teaching-warehouse'],population=[r['id'] for r in records if r['type']=='line'],counts=counts,
        chunks=[dict(number=i,hash=digest(block),count=len(block)) for i,block in enumerate(blocks)],
        windows=[['2026-08-01T00:00:00Z','2026-09-01T00:00:00Z'],['2026-09-01T00:00:00Z','2026-10-02T00:00:00Z']],asOf='2026-11-01T00:00:00Z')
    return manifest,blocks


def policy_starters():
    """Unpublished teaching drafts. A human publishes applicable versions explicitly."""
    return [dict(id=key,title=title,category=category,topics=topics,sections=[dict(id='s1',text=text)],
        region='CN',platform='TEACHING',language='zh',effectiveFrom='2026-01-01T00:00:00Z',
        effectiveUntil='2027-01-01T00:00:00Z',source='中台教学政策（非企业政策）',
        terms=['CLARIFY','MANUAL_REVIEW','SAFETY_ESCALATE'] if key=='safety' else ['CLARIFY','MANUAL_REVIEW']) for key,title,category,topics,text in [
        ('size','尺码与描述核实','APPAREL',['SIZE','DESCRIPTION'],'核对订单明细、商品尺码表与客户说明；存在差异转人工核实，不直接认定质量缺陷。'),
        ('safety','3C安全优先升级','ELECTRONICS',['SAFETY','FUNCTION','COMPATIBILITY'],'冒烟、起火、漏电、异常发热先升级人工安全专员；不指导拆机，不作安全认证或退款承诺。'),
        ('returns','退货资格、时限与费用例外','ALL',['RETURN'],'需核对购买日期、实际履约、申请阶段、适用平台及例外；缺事实时补证。费用和资格必须人工核实，不承诺金额或到账日期。'),
        ('replies','回复承诺与证据适用','ALL',['REPLY'],'回复分别列出客户陈述、已核事实和待补证。仅供内部审核，不自动发出，不宣称退款或ERP工单已完成。')]]
