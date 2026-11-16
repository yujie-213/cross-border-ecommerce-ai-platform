"""D01/D02 bounded source projection, with exact local sourceRead scope.

Raw teaching ERP replies stay in ignored private artifacts. Titles remain titles;
missing conversation, delivery, RMA and product attributes stay unknown.
"""
from pathlib import Path
import json
from .common import require,now,redacted


class SourceReader:
    def __init__(self,factory,allowed_stores,private_root):
        self.factory=factory;self.stores=allowed_stores;self.root=Path(private_root)

    def _store(self,name):
        require(name in self.stores,'SOURCE_SCOPE_DENIED',403)
        return self.stores[name]

    def discover(self,store,check):
        expected=self._store(store);check();reader=self.factory()
        batch=reader.discover('/api/v1/customer-tickets',dict(store_name=store),page_size=20)
        return dict(items=[dict(ticketId=str(r['id']),ticketNumber=r.get('ticket_no'),title=redacted(r.get('subject','')),
            storeName=store,sourceTenant=str(r['tenant_id']),orderLinked=bool(r.get('order_sn')))
            for r in batch.records if str(r.get('tenant_id'))==expected['sourceTenant'] and r.get('store_name')==store],
            complete=batch.complete,observedAt=batch.observed_at,sourceNature='TEACHING_ERP_OBSERVED')

    def verify_mapping(self,identity,check):
        store=next((v for v in self.stores.values() if v['storeId']==identity['storeId'] and v['sourceTenant']==identity['sourceTenant']),None)
        require(store is not None and identity['warehouseMode']=='EXPLICIT_IDS','SOURCE_SCOPE_DENIED',403)
        reader=self.factory();check()
        products=reader.read('/api/v1/products',dict(ids=identity['productId']),page_size=20,max_pages=2)
        require(len(products.records)==1 and str(products.records[0].get('id'))==identity['productId'] and products.records[0].get('sku')==identity['sku']
            and str(products.records[0].get('tenant_id'))==identity['sourceTenant'],'MAPPING_IDENTITY_MISMATCH')
        for wid in identity['warehouseIds']:
            check();wh=reader.read('/api/v1/warehouses',dict(ids=wid),page_size=20,max_pages=2)
            require(len(wh.records)==1 and str(wh.records[0].get('id'))==wid and str(wh.records[0].get('tenant_id'))==identity['sourceTenant'],'MAPPING_WAREHOUSE_MISMATCH')
            check();inventory=reader.read('/api/v1/inventory',dict(field='sku',q=identity['sku'],match='exact',store_id=identity['storeId']),page_size=50,max_pages=2)
            require(inventory.complete and any(str(r.get('product_id'))==identity['productId'] and r.get('sku')==identity['sku']
                and str(r.get('tenant_id'))==identity['sourceTenant'] and str(r.get('store_id'))==identity['storeId']
                and str(r.get('wid'))==wid for r in inventory.records),'MAPPING_RELATION_UNVERIFIED')
        return dict(independentReadback=True,productHash=products.fingerprint,relationVerified=True,observedAt=now())

    def evidence(self,ticket_id,store,check,task_id):
        expected=self._store(store);reader=self.factory();check()
        response=reader.detail('customer-tickets',ticket_id)
        ticket=response.get('data',response)
        if isinstance(ticket,dict) and 'record' in ticket:ticket=ticket['record']
        require(isinstance(ticket,dict) and str(ticket.get('id'))==str(ticket_id) and ticket.get('store_name')==store
            and str(ticket.get('tenant_id'))==expected['sourceTenant'],'SOURCE_IDENTITY_MISMATCH')
        root=self.root/task_id;root.mkdir(parents=True,exist_ok=True)
        (root/'ticket.json').write_text(json.dumps(response,ensure_ascii=False),encoding='utf-8')
        facts=[dict(id='ticket-title',domain='TICKET',kind='OBSERVED',text=redacted(ticket.get('subject','')),sourceRef='customer-tickets:'+str(ticket_id),observedAt=now())]
        missing=['完整客户会话未由工单标题证明','退货申请、实收和退款事实未由工单状态证明','物流追踪号不证明签收']
        order_sn=ticket.get('order_sn');identities=[];business_date=None;association_complete=False
        if order_sn:
            check();batch=reader.read('/api/v1/sales-orders',dict(field='order_sn',q=order_sn),page_size=20,max_pages=2)
            orders=[r for r in batch.records if r.get('order_sn')==order_sn and r.get('store_name')==store and str(r.get('tenant_id'))==expected['sourceTenant']]
            require(len(orders)<=1,'ORDER_AMBIGUOUS')
            (root/'orders.json').write_text(json.dumps(orders,ensure_ascii=False),encoding='utf-8')
            if orders:
                order=orders[0]
                for k in ['payment_status','fulfillment_status','refund_status']:
                    if order.get(k) is not None:facts.append(dict(id='order-'+k,domain=k,kind='OBSERVED',value=order[k],sourceRef='sales-orders:'+str(order['id']),observedAt=now()))
                lines=order.get('item_list') or [];require(isinstance(lines,list),'ORDER_LINES_INVALID')
                association_complete=len(lines)==1
                if len(lines)>10:missing.append('订单超过本次10行取证范围；其余明细未读取，不自动确定受影响商品')
                products_by_sku={}
                for index,line in enumerate(lines[:10]):
                    if not line.get('sku'):continue
                    if line['sku'] not in products_by_sku:
                        try:
                            check();pb=reader.read('/api/v1/products',dict(field='sku',q=line['sku']),page_size=20,max_pages=2)
                            require(pb.complete,'PRODUCT_COVERAGE_INCOMPLETE')
                        except Exception as error:
                            missing.append('商品域未完成核实：'+getattr(error,'code','PRODUCT_READ_FAILED'));break
                        products_by_sku[line['sku']]=[p for p in pb.records if p.get('sku')==line['sku'] and str(p.get('tenant_id'))==expected['sourceTenant']]
                    products=products_by_sku[line['sku']]
                    if len(products)!=1:missing.append('商品真实ID无法唯一核实：'+line['sku']);continue
                    product=products[0]
                    identities.append(dict(lineId=str(order['id'])+':'+str(index),orderId=str(order['id']),productId=str(product['id']),sku=line['sku'],
                        storeId=expected['storeId'],warehouseId=str(expected.get('warehouseId','UNKNOWN')),name=product.get('product_name') or product.get('name') or line['sku'],
                        category='UNKNOWN',attributes={},source='OBSERVED',sourceTenant=expected['sourceTenant']))
                try:
                    check();workflow=reader.detail('sales-workflow',order['id']);w=workflow.get('data',{})
                    (root/'workflow.json').write_text(json.dumps(workflow,ensure_ascii=False),encoding='utf-8')
                    if w.get('paid_at') and w.get('paid_amount') is not None:
                        facts.append(dict(id='paid',domain='PAYMENT',kind='OBSERVED',value=dict(at=w['paid_at'],amount=w['paid_amount'],currency=w.get('currency')),sourceRef='sales-workflow:'+str(order['id']),observedAt=now()))
                    if w.get('shipments'):facts.append(dict(id='shipments',domain='SHIPMENT',kind='OBSERVED',value=[dict(quantity=s.get('item_list'),at=s.get('created_at')) for s in w['shipments']],sourceRef='sales-workflow:'+str(order['id']),observedAt=now()))
                except Exception as error:missing.append('履约域不可用：'+getattr(error,'code','READ_FAILED'))
            else:missing.append('订单精确匹配未找到')
        else:missing.append('工单缺订单号')
        return dict(facts=facts,missing=missing,identityCandidates=identities,identity=identities[0] if association_complete and len(identities)==1 else None,
            businessDate=business_date,title=redacted(ticket.get('subject','')),platform=ticket.get('platform'),observedAt=now(),sourceNature='TEACHING_ERP_OBSERVED',
            sourceRef=dict(ticketId=str(ticket_id),sourceTenant=expected['sourceTenant'],storeId=expected['storeId']))
