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


def policy_starters(region='CN',platform='TEACHING'):
    """Unpublished teaching drafts. A human publishes applicable versions explicitly."""
    return [dict(id=key,title=title,category=category,topics=topics,sections=[dict(id='s1',text=text)],
        region=region,platform=platform,language='zh',effectiveFrom='2026-01-01T00:00:00Z',
        effectiveUntil='2027-01-01T00:00:00Z',source='中台教学政策（非企业政策）',
        terms=['CLARIFY','MANUAL_REVIEW','SAFETY_ESCALATE'] if key=='safety' else ['CLARIFY','MANUAL_REVIEW']) for key,title,category,topics,text in [
        ('size','尺码与描述核实','APPAREL',['SIZE','DESCRIPTION'],'尺码不合适时，先核对订单、履约和现有退货进度。服装在适用退换货期限内、吊牌完整、未穿洗且不影响再次销售，可以申请换货或退货退款；客户未说明的条件用条件句并询问确认。若已提交退货申请，则按当前申请继续跟进，不能重复引导申请或称已退款。商品尺码表或测量缺失时请客户提供实际差异照片，不直接认定质量缺陷。'),
        ('safety','3C安全优先升级','ELECTRONICS',['SAFETY','FUNCTION','COMPATIBILITY'],'冒烟、起火、漏电、异常发热先升级人工安全专员；不指导拆机，不作安全认证或退款承诺。'),
        ('returns','退货资格、时限与费用例外','ALL',['RETURN'],'先核对实际履约和退货申请阶段，避免重复申请。政策条件符合时可申请退货或换货；服装还需吊牌完整、未穿洗、不影响再次销售。退款需退货验收及后续审核完成后依流程办理；申请或退货草稿不代表已退款。具体期限、费用和例外未给定时应询问或核实，不自行编造、不承诺金额或到账日期。'),
        ('replies','回复承诺与证据适用','ALL',['REPLY'],'直接用客户能理解的语气回应诉求，结合系统已核事实和适用政策给出选项与必要条件。已知订单、商品或客户已提供的信息不重复索取，未知事项只问必要问题；不输出给客服的操作指令，不编造已经执行的退款或补发。客服确认保存只留处理记录，不代表已向客户发送。')]]
