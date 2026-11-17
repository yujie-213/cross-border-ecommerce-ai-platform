"""Owned teaching return cohorts, reusing existing store/warehouse/supplier.

Plan by default. No customer notification, refund, procurement or model calls.
Fictional business dates and actual current postings are separately audited.
"""
from __future__ import annotations
import argparse,json,sys
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
from decimal import Decimal

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from tools.b_erp_simulation_dataset import Client,Importer,record,check,fingerprint
from tools.s01_teaching_dataset import canonical_bytes,DatasetError

BATCH='CY-AS-20261117-R2'
DATASET='b-return-cohort-20261117-r2'
SKU='CY-KNIT-021-M'
PRIVATE=ROOT/'data/private/b-return-cohort-20261117-r2'
NATURE='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'


def plan():
    return dict(batch=BATCH,datasetId=DATASET,sourceNature=NATURE,sku=SKU,newStores=0,newWarehouses=0,newSuppliers=0,
        existingStoreId='13',existingWarehouseId='318',existingSupplierId='6',newSkus=1,salesOrders=20,soldUnits=40,
        returnDrafts=8,internalReturnReceipts=6,customerTickets=12,openingUnits=44,
        previousBusinessDates=['2026-11-04','2026-11-10'],currentBusinessDates=['2026-11-11','2026-11-17'],
        posting='CURRENT_REAL_POSTING_WITH_FICTIONAL_SALE_BUSINESS_DATES',
        noRefunds=True,noNotifications=True,noProcurement=True,noModel=True,noHumanRiskDecisions=True)


class DemoClient(Client):
    def __init__(self,root):super().__init__(root);self.owned_returns=set()
    def _allow(self,method,path,*,auth):
        if method=='GET' and path=='/api/v1/customer-voice':return
        parts=path.split('/')
        if method=='POST' and len(parts)==4:
            check(parts[3] in {'products','supplier-quotes','inventory','listings','sales-orders','customer-tickets','sales-returns'},'DEMO_CREATE_SCOPE_DENIED')
        if method=='POST' and len(parts)==6 and parts[3]=='sales-returns':
            check(parts[4] in self.owned_returns and parts[5] in {'authorize','receive'},'DEMO_RETURN_SCOPE_DENIED');return
        super()._allow(method,path,auth=auth)


class DemoImporter(Importer):
    def __init__(self,root=PRIVATE,client=None):
        root.mkdir(parents=True,exist_ok=True);self.root=root;self.path=root/'journal.json'
        self.journal=json.loads(self.path.read_bytes()) if self.path.exists() else dict(batch=BATCH,plan=plan(),operations={},state='PLANNED')
        check(self.journal['batch']==BATCH and self.journal['plan']==plan(),'JOURNAL_CONFLICT')
        self.client=client or DemoClient(root)

    def preflight(self):
        me=record(self.client.request('GET','/api/v1/me'))
        contract=record(self.client.request('GET','/api/v1/data-contract'))
        check(str(me.get('tenant_id'))=='1' and contract.get('kind')=='synthetic','SYNTHETIC_SCOPE_REQUIRED')
        store=record(self.client.request('GET','/api/v1/store-authorizations/13'))
        warehouse=record(self.client.request('GET','/api/v1/warehouses/318'))
        supplier=record(self.client.request('GET','/api/v1/suppliers/6'))
        check(store.get('store_name')=='SIM-AS-20261116-R1-SHOP' and str(store.get('tenant_id'))=='1'
            and str(warehouse.get('tenant_id'))=='1' and str(supplier.get('tenant_id'))=='1','EXISTING_RESOURCE_DRIFT')
        self.journal['preflight']=dict(at=datetime.now(timezone.utc).isoformat(),contractDigest=fingerprint(contract),store=store,warehouse=warehouse,supplier=supplier)
        self.save();return store,warehouse,supplier

    def return_action(self,draft,action,quality=None):
        rid=str(draft['id']);self.client.owned_returns.add(rid);key='return:'+rid+':'+action
        payload={} if action=='authorize' else dict(quality_list=quality)
        prior=self.journal['operations'].get(key)
        check(prior is None or prior['fingerprint']==fingerprint(payload),'RETURN_PAYLOAD_CHANGED')
        before=record(self.client.request('GET','/api/v1/sales-returns/'+rid))
        check(before.get('local_only') is True and before.get('order_id')==draft['order_id'],'NONLOCAL_RETURN_DENIED')
        expected='authorized' if action=='authorize' else 'received'
        if not prior:
            check(before.get('state')==('draft' if action=='authorize' else 'authorized'),'RETURN_STATE_CHANGED')
            self.journal['operations'][key]=dict(state='SENDING',fingerprint=fingerprint(payload),payload=payload);self.save()
            try:self.client.request('POST','/api/v1/sales-returns/'+rid+'/'+action,payload)
            except Exception:self.journal['operations'][key]['state']='UNKNOWN';self.save();raise
        after=record(self.client.request('GET','/api/v1/sales-returns/'+rid))
        check(after.get('local_only') is True and (after.get('authorized_at') if action=='authorize' else after.get('received_at')),'RETURN_READBACK_MISSING')
        if action=='receive':check(after.get('quality_list')==quality and after.get('inbound_id') and after.get('refunded_at') is None,'RETURN_QUALITY_MISMATCH')
        self.journal['operations'][key].update(state='VERIFIED',record=after);self.save();return after

    def owned_return(self,number,payload):
        op=self.journal['operations'].get('sales-returns:'+number)
        if op and op.get('state')=='VERIFIED':
            result=record(self.client.request('GET','/api/v1/sales-returns/'+op['erpId']))
            check(result.get('return_no')==number and result.get('order_id')==payload['order_id']
                and result.get('reason')==payload['reason'] and result.get('item_list')==payload['item_list'],'RETURN_IDENTITY_DRIFT')
            return result
        return self.create('sales-returns','return_no',number,payload)

    def execute(self):
        store,warehouse,supplier=self.preflight()
        p=self.create('products','sku',SKU,dict(sku=SKU,name='澄屿细针织开衫 M 雾蓝',category='服装/针织衫',model='CY-021-M-BL',
            material='棉60% / 聚酯纤维40%',status='在售',unit='piece',price=29,cost=8,product_type='普通商品',brand='澄屿',
            owner='CommerceHub',description='雾蓝色圆领开衫，M码，日常通勤穿着。',supplier_name=supplier['name'],moq=8,procurement_lead_days=3,default_carton_qty=4))
        qno=BATCH+'-Q1'
        quote=self.create('supplier-quotes','quote_no',qno,dict(quote_no=qno,supplier_code=supplier['supplier_code'],sku=SKU,
            currency='USD',unit_price='8.00',minimum_quantity=8,lead_days=3,valid_from='2026-11-01',valid_to='2027-11-17',enabled=True,expected_version=0,request_key=qno+'-CREATE'))
        inv=self.create('inventory','batch_no',BATCH+'-I1',dict(batch_no=BATCH+'-I1',wid=warehouse['id'],warehouse_name=warehouse['name'],
            product_id=p['id'],sku=SKU,store_id=store['id'],store_name=store['store_name'],quantity=44,available=44,source_batch_no=BATCH,order_sn=BATCH+'-OPEN'))
        listing=self.create('listings','listing_id',BATCH+'-L1',dict(sku=SKU,platform='Amazon',store_name=store['store_name'],listing_id=BATCH+'-L1',title=p['name'],price=29,stock=44,status_text='在售'))
        names=['林知夏','沈若宁','许嘉言','陈以安','苏念初','周星禾','江予晴','顾晚棠','温景和','何清越']
        sales=[]
        for i in range(20):
            day=date(2026,11,4 if i<10 else 11)+timedelta(days=(i%10)*6//9)
            number='CY-261117-'+f'{i+1:04}'
            sale=self.create('sales-orders','order_sn',number,dict(order_sn=number,platform_order_sn=number,platform='Amazon',store_name=store['store_name'],site='US',country='US',
                buyer=names[i%10],phone='',shipping_address='',order_time=day.isoformat()+' 12:00:00',currency='USD',amount=58,shipping_warehouse=warehouse['name'],delivery_method='TEACHING_LOCAL_ONLY',
                remark='开衫订单',item_list=[dict(sku=SKU,product_id=p['id'],quantity=2,unit_price=29,amount=58)]))
            self.workflow(sale,'record-payment',dict(reference=number+'-PAY',amount='58.00',currency='USD'))
            self.workflow(sale,'ship',dict(carrier='TEACHING_LOCAL_ONLY',tracking_no=number+'-SHIP'))
            sales.append(record(self.client.request('GET','/api/v1/sales-orders/'+str(sale['id']))))
        reasons=['收到后发现袖口有一段缝线松开，希望换一件。','左袖口接缝开线，试穿前就看到了，申请退货。','衣服颜色喜欢，但肩部接缝松脱，希望换货。','正常穿着后侧缝松开，附有问题照片，想退货。','拆包时看到下摆接缝裂开，申请换同码。','第一次穿着后袖口开线，希望办理退货。','尺码略紧，吊牌还在，想换大一码。','颜色比预期浅，未穿洗，咨询能否退货。']
        returns=[]
        for i,order_index in enumerate([0,10,11,12,13,14,15,16]):
            number='CY-R261117-'+f'{i+1:03}'
            draft=self.owned_return(number,dict(return_no=number,order_id=sales[order_index]['id'],reason=reasons[i],item_list=[dict(sku=SKU,quantity=1)],refund_amount='29.00',currency='USD'))
            if i<6:
                self.return_action(draft,'authorize')
                draft=self.return_action(draft,'receive',[dict(sku=SKU,good_qty=0,bad_qty=1)])
            returns.append(draft)
        messages=reasons+['面料柔软，颜色很满意，感谢。','尺码合适，发货及时，穿着舒服。','包装完整，希望了解日常清洗方式。','物流比预期慢一天，已经收到，商品没有问题。']
        tickets=[]
        for i,text in enumerate(messages):
            sale=sales[([0,10,11,12,13,14,15,16]+[17,18,19,9])[i]]
            tickets.append(self.create('customer-tickets','ticket_no','CY-C261117-'+f'{i+1:03}',dict(ticket_no='CY-C261117-'+f'{i+1:03}',platform='Amazon',store_name=store['store_name'],buyer=sale['buyer'],subject=text,status_text='待处理',owner='售后服务组',created_time='2026-11-17 12:00:00',order_sn=sale['order_sn'])))
        final=record(self.client.request('GET','/api/v1/inventory/'+str(inv['id'])))
        ledger=self.client.request('GET','/api/v1/stock/ledger',dict(sku=SKU,warehouse_name=warehouse['name'],offset=0,limit=200))
        check(ledger.get('total')==len(ledger.get('items',[])),'LEDGER_INCOMPLETE')
        rows=sorted(ledger['items'],key=lambda r:r['id']);running=Decimal(str(rows[0]['before_quantity']));available=Decimal(str(rows[0]['before_available']))
        for row in rows:
            check(str(row['inventory_id'])==str(inv['id']) and Decimal(str(row['before_quantity']))==running and Decimal(str(row['before_available']))==available,'LEDGER_CONTINUITY_FAILED')
            running+=Decimal(str(row['delta_quantity']));available+=Decimal(str(row['delta_available']))
            check(running==Decimal(str(row['after_quantity'])) and available==Decimal(str(row['after_available'])),'LEDGER_ARITHMETIC_FAILED')
        check(running==Decimal(str(final['quantity'])) and available==Decimal(str(final['available'])),'STOCK_READBACK_MISMATCH')
        self.sync_listing(listing,int(final['available']))
        member=dict(product=p,store=store,warehouse=warehouse,supplier=supplier,quote=quote,inventory=final,listing=listing,sales=sales,ledger=rows,opening=44)
        self.journal.update(member=member,tickets=tickets,returns=returns,state='ERP_VERIFIED');self.save()
        self.register_member(member)
        self.write_customer_context(member,tickets)
        from commerce_hub.bootstrap.after_sales import source_reader
        from commerce_hub.bootstrap.local_platform import configure
        snapshot=source_reader(configure()).return_analysis(store['store_name'],lambda:None,end_date='2026-11-17')
        metric=next(row for row in snapshot['monitor'] if row['sku']==SKU)
        check(snapshot['complete'] and metric['previous']==20 and metric['current']==20 and metric['previousReturns']==1 and metric['currentReturns']==5,'COHORT_READBACK_FAILED')
        self.journal.update(state='REGISTERED_AND_ANALYZED',metric=metric);self.save()
        print(json.dumps(dict(state=self.journal['state'],sku=SKU,sales=20,tickets=12,receivedReturns=6,draftReturns=2,stock=final['available'],previousReturnRate=metric['previousReturnRate'],currentReturnRate=metric['currentReturnRate'],reads=self.client.counts),ensure_ascii=False))

    def register_member(self,m):
        from commerce_hub.data.sync.online import OnlineMapping
        from commerce_hub.data.projection.monitor import MonitorRegistry
        from commerce_hub.bootstrap.local_platform import configure
        from commerce_hub.infrastructure.database import Database
        scope=dict(tenantId='s01-owned-teaching-local',storeIds=['13'],warehouseIds=['318'],canonicalSkuIds=[SKU],fields=['quantity'])
        binding=dict(datasetId=DATASET,scopeVersion=1,importBatchId=BATCH,productId=str(m['product']['id']),listingId=str(m['listing']['id']),supplierId=str(m['supplier']['id']),quoteId=str(m['quote']['id']),quoteNo=m['quote']['quote_no'],
            inventoryIds=[str(m['inventory']['id'])],salesIds=[str(s['id']) for s in m['sales']],openingQuantity='44',evidenceDigest=fingerprint(m))
        mapping=OnlineMapping(scope=scope,sku=SKU,sourceTenant='1',sourceStore='13',sourceWarehouse='318',storeName=m['store']['store_name'],warehouseName=m['warehouse']['name'],monitor=binding).validate_scope()
        (self.root/'mappings.json').write_bytes(canonical_bytes([mapping.model_dump(mode='json')]))
        db=Database(configure())
        try:
            reg=MonitorRegistry(db.engine,'s01-owned-teaching-local');before=[x for x in reg.mappings() if x.monitor.datasetId!=DATASET]
            reg.activate([mapping.model_dump(mode='json')],'owner-authorized-after-sales-flow-20261117')
            check(before==[x for x in reg.mappings() if x.monitor.datasetId!=DATASET],'EXISTING_MEMBERS_CHANGED')
        finally:db.close()

    def write_customer_context(self,m,tickets):
        from commerce_hub.scenarios.after_sales.customer_context import NATURE as CONTEXT_NATURE
        path=ROOT/'data/private/b-after-sales/customer-context.json'
        body=json.loads(path.read_bytes()) if path.exists() else dict(schemaVersion='1.0.0',datasetId=DATASET,version='v1',sourceNature=CONTEXT_NATURE,items=[])
        for ticket in tickets:
            sale=next(s for s in m['sales'] if s['order_sn']==ticket['order_sn'])
            item=dict(erpTicketId=str(ticket['id']),erpStoreName=m['store']['store_name'],sourceTenant='1',storeId='13',orderId=str(sale['id']),orderNumber=sale['order_sn'],productId=str(m['product']['id']),sku=SKU,
                provenance='SUPPLEMENTAL_SIMULATED_CUSTOMER_STATEMENT',text=ticket['subject'],at='2026-11-17T12:00:00+08:00')
            old=next((i for i in body['items'] if i['erpTicketId']==item['erpTicketId']),None)
            check(old is None or old==item,'CONTEXT_CONFLICT')
            if not old:body['items'].append(item)
        path.write_bytes(canonical_bytes(body))


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute-live',action='store_true');parser.add_argument('--preflight',action='store_true');args=parser.parse_args()
    if not args.execute_live and not args.preflight:print(json.dumps(plan(),ensure_ascii=False,indent=2))
    else:
        try:
            importer=DemoImporter();importer.execute() if args.execute_live else importer.preflight()
        except Exception as e:
            print(json.dumps(dict(state='STOPPED',error=getattr(e,'code',type(e).__name__),status=getattr(e,'status',None))));raise SystemExit(1) from None
