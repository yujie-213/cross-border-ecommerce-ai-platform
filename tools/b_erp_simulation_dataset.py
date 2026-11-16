"""Owner-authorized 3-SKU ERP simulation, with durable write/readback recovery.

Default: plan only. --preflight performs bounded reads. --execute-live imports
fictional records in the synthetic teaching ERP only. No procurement, approval,
refund, return receipt, external delivery/message, paid model or ERP SQL access.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from dotenv import dotenv_values
from tools.s01_teaching_dataset import TeachingDatasetClient, Config, DatasetError, canonical_bytes

BATCH = 'SIM-AS-20261116-R1'
DATASET = 'b-s01-simulated-20261116-r1'
NATURE = 'SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'
PRIVATE = ROOT / 'data/private/b-erp-simulation-20261116-r1'
PUBLIC = ROOT / 'docs/evidence/B-ERP-SIMULATION-20261116'
COLLECTIONS = {'products', 'inventory', 'listings', 'store-authorizations',
               'warehouses', 'suppliers', 'supplier-quotes', 'sales-orders',
               'customer-tickets', 'sales-returns'}


def check(ok, code):
    if not ok:
        raise DatasetError(code)


def fingerprint(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def profiles():
    return [
        dict(sku='SIM-AS-261116-KNIT-M', name='澄屿圆领针织衫 M 藏青（完全仿真）',
             category='服装/针织衫', material='棉60% / 聚酯纤维40%', model='CY-KNIT-M-NV',
             price=24, cost=6, closing=3, quantities=[2,2,3,3,4,4,5,5,6,6],
             description='M码；藏青；圆领长袖；仅教学仿真，非现实商品',
             tickets=[
                 '穿着一天后袖口接缝出现开线，想了解换货流程。未寄回，尚无实物检验。',
                 '拆包时看到左侧接缝松散，有线头；希望先核实处理方式。未寄回。',
                 '第一次轻柔手洗后下摆接缝开线，申请退货；尚无实物检验。',
                 '收到后发现袖口缝线脱落，希望换同款；尚无实物检验。',
                 '穿着后肩部接缝松开，申请退货；尚无实物检验。',
                 '试穿时侧缝开线，担心后续使用，希望客服帮助；尚无实物检验。',
                 '首次穿着后下摆缝线脱落，希望了解退换政策；尚无实物检验。']),
        dict(sku='SIM-AS-261116-CABLE', name='澄屿USB-C编织线 1m 灰（完全仿真）',
             category='电子/数码配件', material='尼龙编织 / 铝合金接头', model='CY-C60-GY',
             price=10, cost=2, closing=4, quantities=[2]*10,
             description='USB-C双头；60W；1m；无电池；仅教学仿真',
             tickets=[
                 '本地模拟物流记录尚未显示签收，想查询进度；没有反馈商品损坏。',
                 '包裹外盒有压痕，尚未拆开检查商品，想了解如何核实；未证实产品缺陷。',
                 '模拟包裹比预计晚到，希望了解配送情况；商品功能尚未检查。']),
        dict(sku='SIM-AS-261116-POUCH', name='澄屿帆布收纳袋 米白（完全仿真）',
             category='家居/收纳用品', material='棉帆布 / 金属拉链', model='CY-P28-IV',
             price=15, cost=3, closing=80, quantities=[1]*10,
             description='28×20×8cm；米白；无认证声明；仅教学仿真',
             tickets=['想了解帆布袋的清洗和晾晒方法，商品未发现质量问题。',
                      '颜色与个人预期不同，想咨询未使用商品能否退换；未声称质量缺陷。'])]


def plan():
    # Actual current posting is never represented as historical ERP posting.
    days=[date(2026,11,9)+timedelta(days=i) for i in [0,1,2,3,4,4,5,5,6,6]]
    return dict(batch=BATCH,datasetId=DATASET,sourceNature=NATURE,
                newSkus=3,salesOrders=30,customerTickets=12,returnDrafts=7,
                newStores=1,newWarehouses=1,newSuppliers=1,supplierQuotes=3,
                inventoryRows=3,listings=3,saleBusinessDates=[d.isoformat() for d in days],
                maxMutationAttempts=127,maxReadAttempts=700,
                history='FICTIONAL_BUSINESS_DATES_CURRENT_REAL_POSTING',
                noExternalTransactions=True,noModelCalls=True,noHumanRiskDecisions=True)


class Client(TeachingDatasetClient):
    def __init__(self, root=PRIVATE):
        v=dotenv_values(ROOT/'.env.erp',interpolate=False)
        super().__init__(Config(v.get('ERP_USERNAME') or '',v.get('ERP_PASSWORD') or '',
                               v.get('ERP_ACCESS_TOKEN') or '',timeout=20),root/'raw')
        self.root=root
        self.owned_sales=set()
        self.owned_listing_paths=set()
        self.events_path=root/'requests.jsonl'
        self.counts={'GET':0,'POST':0,'PUT':0}
        if self.events_path.exists():
            for line in self.events_path.read_text(encoding='utf-8').splitlines():
                e=json.loads(line)
                self.counts[e['method']]=self.counts.get(e['method'],0)+1

    def authenticate(self):
        if self.token:return
        check(bool(self.config.username and self.config.password),'ERP_CREDENTIALS_MISSING')
        status,raw=self._transport('POST','/api/auth-server/oauth/access-token',
            {'Content-Type':'application/json'},canonical_bytes(dict(appId=self.config.username,appSecret=self.config.password)))
        check(status==200,'ERP_AUTH_REJECTED')
        self.token=json.loads(raw).get('data',{}).get('access_token')
        check(isinstance(self.token,str) and bool(self.token) and '\n' not in self.token and '\r' not in self.token,
              'ERP_AUTH_ENVELOPE_REJECTED')
        # Neither authentication body nor token is persisted or printed.

    def _allow(self, method, path, *, auth):
        check(not auth and '://' not in path and '?' not in path and '..' not in path,'OPERATION_DENIED')
        parts=path.split('/')
        if method=='GET' and path in {'/api/v1/me','/api/v1/data-contract','/api/v1/stock/ledger'}:return
        if method=='GET' and len(parts) in {4,5} and parts[3] in COLLECTIONS|{'sales-workflow','outbound-orders','finance'}:return
        if method=='POST' and len(parts)==4 and parts[3] in COLLECTIONS:return
        if method=='PUT' and path in self.owned_listing_paths:return
        if (method=='POST' and len(parts)==6 and parts[3]=='sales-workflow'
            and parts[4] in self.owned_sales and parts[5] in {'record-payment','ship'}):return
        raise DatasetError('OPERATION_DENIED')

    def request(self,method,path,values=None,**kwargs):
        self._allow(method,path,auth=False)
        check(self.counts['GET']<700 if method=='GET' else self.counts['POST']+self.counts['PUT']<127,
              'BATCH_REQUEST_LIMIT')
        self.counts[method]+=1
        event=dict(method=method,path=path,at=datetime.now(timezone.utc).isoformat(),state='SENDING')
        with self.events_path.open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
        time.sleep(.35)
        try:
            result,sha,at,ref=super().request(method,path,values,**kwargs)
        except Exception:raise
        return result

    def exact(self,resource,key,value,*,order_id=None):
        if resource=='sales-returns':check(type(order_id) is int and order_id>0,'EXACT_RETURN_ORDER_REQUIRED')
        params=dict(quote_no=value) if resource=='supplier-quotes' else (
            dict(order_id=order_id) if resource=='sales-returns' else dict(field=key,q=value,match='exact'))
        result=self.request('GET','/api/v1/'+resource,dict(params,offset=0,limit=50,
                            **({'view':'full'} if resource in {'inventory','sales-orders'} else {})))
        rows=result.get('items')
        check(isinstance(rows,list) and result.get('total')==len(rows) and len(rows)<=1,'EXACT_LOOKUP_INCOMPLETE_OR_AMBIGUOUS')
        check(all(str(r.get(key))==str(value) for r in rows),'EXACT_LOOKUP_MISMATCH')
        return rows


def record(result):
    return result.get('data',result)


class Importer:
    def __init__(self,root=PRIVATE,client=None):
        root.mkdir(parents=True,exist_ok=True)
        self.root=root;self.path=root/'journal.json'
        self.journal=json.loads(self.path.read_bytes()) if self.path.exists() else dict(
            batch=BATCH,sourceNature=NATURE,plan=plan(),operations={},state='PLANNED')
        check(self.journal['batch']==BATCH and self.journal['plan']==plan(),'JOURNAL_CONFLICT')
        self.client=client or Client(root)

    def save(self):
        tmp=self.path.with_suffix('.part');tmp.write_bytes(canonical_bytes(self.journal));tmp.replace(self.path)

    def preflight(self):
        check(datetime.now(timezone(timedelta(hours=8))).date()==date(2026,11,16),'EXPLICIT_BATCH_DATE_REQUIRED')
        schema=json.loads((ROOT/'docs/ERP-openapi.yaml').read_bytes())
        for resource in COLLECTIONS:
            check('post' in schema['paths'].get('/api/v1/'+resource,{}),'CREATE_CONTRACT_MISSING')
        for action in ['record-payment','ship']:
            check('post' in schema['paths'].get('/api/v1/sales-workflow/{id}/'+action,{}),'WORKFLOW_CONTRACT_MISSING')
        me=record(self.client.request('GET','/api/v1/me'))
        check(str(me.get('tenant_id'))=='1' and '*' in me.get('permissions',[]),'TEACHING_ACCOUNT_SCOPE_DENIED')
        contract=self.client.request('GET','/api/v1/data-contract')
        check(contract.get('kind')=='synthetic','SYNTHETIC_TEACHING_ERP_REQUIRED')
        self.journal['preflight']=dict(at=datetime.now(timezone.utc).isoformat(),sourceTenant='1',
            sourceKind=contract['kind'],contractDigest=fingerprint(contract),openapiDigest=fingerprint(schema),
            noExternalActions=True)
        self.save()
        print(json.dumps(dict(preflight='PASS',sourceKind='synthetic',plan=plan()),ensure_ascii=False),flush=True)

    def create(self,resource,key,value,payload):
        name=resource+':'+str(value);ops=self.journal['operations'];prior=ops.get(name)
        fp=fingerprint(payload)
        check(prior is None or prior['fingerprint']==fp,'PAYLOAD_CHANGED')
        lookup=dict(order_id=payload['order_id']) if resource=='sales-returns' else {}
        found=self.client.exact(resource,key,value,**lookup)
        if found:
            check(prior is not None,'EXISTING_RECORD_NOT_OWNED')
        else:
            check(prior is None,'UNKNOWN_WRITE_NOT_FOUND_NO_RESEND')
            ops[name]=dict(state='SENDING',fingerprint=fp,payload=payload,resource=resource)
            self.save()
            try:self.client.request('POST','/api/v1/'+resource,payload)
            except Exception:
                ops[name]['state']='UNKNOWN';self.save();raise
            found=self.client.exact(resource,key,value,**lookup)
            check(len(found)==1,'INDEPENDENT_READBACK_MISSING')
        actual=found[0]
        ignored={'expected_version','request_key','supplier_code'} if resource=='supplier-quotes' else set()
        if resource=='inventory' and prior and prior.get('state')=='VERIFIED':ignored|={'quantity','available'}
        if resource=='listings' and prior and prior.get('state')=='VERIFIED':ignored.add('stock')
        for k,v in payload.items():
            check(k in ignored or actual.get(k)==v or str(actual.get(k))==str(v),
                  'READBACK_FIELD_MISMATCH_'+resource+'_'+k)
        if resource not in {'sales-returns','supplier-quotes'}:
            check(str(actual.get('tenant_id'))=='1','FOREIGN_TENANT_READBACK')
        elif resource=='sales-returns':
            check(actual.get('local_only') is True and actual.get('state')=='draft','LOCAL_DRAFT_REQUIRED')
        if prior and prior.get('erpId'):check(str(actual['id'])==prior['erpId'],'ERP_ID_DRIFT')
        ops[name].update(state='VERIFIED',erpId=str(actual['id']),record=actual);self.save()
        print(json.dumps(dict(verified=resource,id=actual['id'])),flush=True)
        return actual

    def workflow(self,sale,action,payload):
        sid=str(sale['id']);self.client.owned_sales.add(sid)
        name='workflow:'+sid+':'+action;prior=self.journal['operations'].get(name)
        check(prior is None or prior['fingerprint']==fingerprint(payload),'WORKFLOW_PAYLOAD_CHANGED')
        before=record(self.client.request('GET','/api/v1/sales-workflow/'+sid))
        check(before.get('local_only') is True and before.get('order_id')==sale['id'],'LOCAL_ONLY_ORDER_REQUIRED')
        if not prior:
            expected='unpaid' if action=='record-payment' else 'paid'
            check(before.get('state')==expected,'UNEXPECTED_WORKFLOW_STATE')
            self.journal['operations'][name]=dict(state='SENDING',fingerprint=fingerprint(payload),payload=payload)
            self.save()
            try:self.client.request('POST','/api/v1/sales-workflow/'+sid+'/'+action,payload)
            except Exception:
                self.journal['operations'][name]['state']='UNKNOWN';self.save();raise
        after=record(self.client.request('GET','/api/v1/sales-workflow/'+sid))
        check(after.get('local_only') is True,'NONLOCAL_WORKFLOW_REJECTED')
        if action=='record-payment':
            check(after.get('payment_reference')==payload['reference'] and Decimal(after['paid_amount'])==Decimal(payload['amount'])
                  and after.get('currency')==payload['currency'],'PAYMENT_READBACK_MISMATCH')
        else:
            check(after.get('state')=='shipped' and len(after.get('shipments',[]))==1
                  and after['shipments'][0].get('tracking_no')==payload['tracking_no']
                  and after['shipments'][0].get('carrier')=='TEACHING_LOCAL_ONLY','SHIPMENT_READBACK_MISMATCH')
        self.journal['operations'][name].update(state='VERIFIED',workflow=after);self.save()

    def sync_listing(self,listing,quantity):
        path='/api/v1/listings/'+str(listing['id']);self.client.owned_listing_paths.add(path)
        name='listing-stock:'+str(listing['id']);prior=self.journal['operations'].get(name)
        current=record(self.client.request('GET',path))
        check(current.get('listing_id')==listing['listing_id'] and current.get('sku')==listing['sku'],'LISTING_IDENTITY_DRIFT')
        if current.get('stock')!=quantity:
            check(prior is None,'UNKNOWN_LISTING_UPDATE_NO_RESEND')
            self.journal['operations'][name]=dict(state='SENDING',quantity=quantity);self.save()
            try:self.client.request('PUT',path,dict(stock=quantity))
            except Exception:
                self.journal['operations'][name]['state']='UNKNOWN';self.save();raise
            current=record(self.client.request('GET',path))
            check(current.get('stock')==quantity,'LISTING_STOCK_READBACK_MISMATCH')
        self.journal['operations'][name]=dict(state='VERIFIED',quantity=quantity);self.save()

    def execute(self):
        self.preflight()
        st=self.create('store-authorizations','store_name',BATCH+'-SHOP',dict(
            store_name=BATCH+'-SHOP',platform='Amazon',site='US',status_text='已授权',fee_rate=0))
        wh=self.create('warehouses','warehouse_code',BATCH+'-WH',dict(
            warehouse_code=BATCH+'-WH',name='澄屿完全仿真教学仓-261116',warehouse_type='自营仓',country='US',status_text='正常'))
        su=self.create('suppliers','supplier_code',BATCH+'-SUP',dict(
            supplier_code=BATCH+'-SUP',name='澄屿完全仿真教学供应商-261116',status_text='正常',purchase_user='虚构教学采购组'))
        members=[];tickets=[];returns=[]
        for pi,p in enumerate(profiles()):
            sku=p['sku'];opening=sum(p['quantities'])+p['closing']
            product=self.create('products','sku',sku,dict(sku=sku,name=p['name'],category=p['category'],model=p['model'],
                material=p['material'],status='在售',unit='piece',price=p['price'],cost=p['cost'],product_type='普通商品',
                brand='澄屿（虚构教学品牌）',tag=BATCH,owner='CommerceHub',description=p['description']+'；'+NATURE+'；'+DATASET,
                supplier_name=su['name'],moq=8,procurement_lead_days=3,default_carton_qty=4))
            qno=BATCH+'-Q-'+str(pi+1)
            quote=self.create('supplier-quotes','quote_no',qno,dict(quote_no=qno,supplier_code=su['supplier_code'],
                sku=sku,currency='USD',unit_price=f"{p['cost']:.2f}",minimum_quantity=8,lead_days=3,
                valid_from='2026-11-09',valid_to='2027-11-16',enabled=True,expected_version=0,request_key=qno+'-CREATE'))
            check(str(quote.get('product_id'))==str(product['id']) and str(quote.get('supplier_id'))==str(su['id']),'QUOTE_RELATION_MISMATCH')
            inv=self.create('inventory','batch_no',BATCH+'-INV-'+str(pi+1),dict(batch_no=BATCH+'-INV-'+str(pi+1),
                wid=wh['id'],warehouse_name=wh['name'],product_id=product['id'],sku=sku,store_id=st['id'],store_name=st['store_name'],
                quantity=opening,available=opening,source_batch_no=BATCH,order_sn=BATCH+'-OPEN-'+str(pi+1)))
            listing=self.create('listings','listing_id',BATCH+'-L-'+str(pi+1),dict(sku=sku,platform='Amazon',store_name=st['store_name'],
                listing_id=BATCH+'-L-'+str(pi+1),title=p['name'],price=p['price'],stock=opening,status_text='在售'))
            sales=[];ledger=[]
            for si,(day,qty) in enumerate(zip(plan()['saleBusinessDates'],p['quantities'])):
                number=BATCH+'-S-'+str(pi+1)+'-'+f'{si+1:02}'
                sale=self.create('sales-orders','order_sn',number,dict(order_sn=number,platform_order_sn=number,
                    platform='Amazon',store_name=st['store_name'],site='US',country='US',buyer='SIMULATED-BUYER-'+str(pi+1)+'-'+str(si+1),
                    phone='',shipping_address='SIMULATION ONLY / NO REAL DELIVERY ADDRESS',
                    order_time=day+' 12:00:00',currency='USD',amount=qty*p['price'],shipping_warehouse=wh['name'],
                    delivery_method='TEACHING_LOCAL_ONLY',remark=NATURE+';'+BATCH+';fictional business date/current actual posting',
                    item_list=[dict(sku=sku,product_id=product['id'],quantity=qty,unit_price=p['price'],amount=qty*p['price'])]))
                self.workflow(sale,'record-payment',dict(reference=number+'-PAY',amount=f"{qty*p['price']:.2f}",currency='USD'))
                self.workflow(sale,'ship',dict(carrier='TEACHING_LOCAL_ONLY',tracking_no=number+'-SHIP'))
                current=record(self.client.request('GET','/api/v1/sales-orders/'+str(sale['id'])))
                check(current.get('payment_status')=='已支付' and current.get('fulfillment_status')=='已发货'
                      and current.get('refund_status')=='无退款','SALE_STATE_MISMATCH')
                wf=self.journal['operations']['workflow:'+str(sale['id'])+':ship']['workflow']
                ship=wf['shipments'][0]
                movement=self.client.request('GET','/api/v1/stock/ledger',dict(resource='outbound-orders',record_id=ship['outbound_id'],offset=0,limit=20))
                check(movement.get('total')==1 and len(movement.get('items',[]))==1,'EXACT_LEDGER_INCOMPLETE')
                row=movement['items'][0]
                check(row.get('sku')==sku and str(row.get('inventory_id'))==str(inv['id'])
                      and row.get('delta_quantity')==-qty and row.get('delta_available')==-qty,'LEDGER_RELATION_MISMATCH')
                ledger.append(row);sales.append(current)
            final=record(self.client.request('GET','/api/v1/inventory/'+str(inv['id'])))
            running=opening
            for row in sorted(ledger,key=lambda r:r['id']):
                check(row['before_quantity']==running and row['before_available']==running,'LEDGER_CONTINUITY_FAILED')
                running+=row['delta_quantity']
                check(row['after_quantity']==running and row['after_available']==running,'LEDGER_ARITHMETIC_FAILED')
            check(running==p['closing']==final['quantity']==final['available'],'FINAL_STOCK_MISMATCH')
            self.sync_listing(listing,running)
            for ti,statement in enumerate(p['tickets']):
                sale=sales[ti];number=BATCH+'-T-'+str(pi+1)+'-'+str(ti+1)
                ticket=self.create('customer-tickets','ticket_no',number,dict(ticket_no=number,platform='Amazon',store_name=st['store_name'],
                    buyer=sale['buyer'],subject='【完全仿真客户陈述】'+statement,status_text='待处理',owner='虚构教学售后组',
                    created_time='2026-11-16 12:00:00',order_sn=sale['order_sn']))
                tickets.append(ticket)
                if pi==0:
                    rno=BATCH+'-RET-'+str(ti+1)
                    draft=self.create('sales-returns','return_no',rno,dict(return_no=rno,order_id=sale['id'],
                        reason='【完全仿真／未证实】'+statement,item_list=[dict(sku=sku,quantity=1)],refund_amount=f"{p['price']:.2f}",currency='USD'))
                    check(draft.get('authorized_at') is None and draft.get('received_at') is None and draft.get('refunded_at') is None
                          and draft.get('finance_id') is None and draft.get('inbound_id') is None,'RETURN_DRAFT_HAS_SIDE_EFFECT')
                    returns.append(draft)
            members.append(dict(profile=p,product=product,store=st,warehouse=wh,supplier=su,quote=quote,
                inventory=final,listing=listing,sales=sales,ledger=ledger,opening=opening,closing=running))
            self.journal.update(members=members,tickets=tickets,returns=returns);self.save()
        check(len(members)==3 and len(tickets)==12 and len(returns)==7,'BATCH_COUNTS_MISMATCH')
        self.journal['state']='ERP_INDEPENDENTLY_VERIFIED';self.save()
        mappings=self.make_mappings(members)
        self.verify_replenishment(mappings)
        self.register(mappings)
        self.verify_after_sales()
        self.journal['state']='REGISTERED_AND_READABLE';self.save()
        self.summary()

    def make_mappings(self,members):
        from commerce_hub.data.sync.online import OnlineMapping
        result=[]
        for m in members:
            sku=m['product']['sku'];sid=str(m['store']['id']);wid=str(m['warehouse']['id'])
            scope=dict(tenantId='s01-owned-teaching-local',storeIds=[sid],warehouseIds=[wid],canonicalSkuIds=[sku],fields=['quantity'])
            binding=dict(datasetId=DATASET,scopeVersion=1,importBatchId=BATCH,productId=str(m['product']['id']),
                listingId=str(m['listing']['id']),supplierId=str(m['supplier']['id']),quoteId=str(m['quote']['id']),quoteNo=m['quote']['quote_no'],
                inventoryIds=[str(m['inventory']['id'])],salesIds=[str(s['id']) for s in m['sales']],purchaseIds=[],
                openingQuantity=str(m['opening']),evidenceDigest=fingerprint(m))
            result.append(OnlineMapping(scope=scope,sku=sku,sourceTenant='1',sourceStore=sid,sourceWarehouse=wid,
                storeName=m['store']['store_name'],warehouseName=m['warehouse']['name'],monitor=binding).validate_scope())
        (self.root/'mappings.json').write_bytes(canonical_bytes([m.model_dump(mode='json') for m in result]))
        return result

    def verify_replenishment(self,mappings):
        from commerce_hub.adapters.erp import ERPConfig,TeachingERPReader
        from commerce_hub.bootstrap.s01_v2 import erp_config
        from commerce_hub.data.sync.online import collect
        from commerce_hub.data.projection.online import observed,normalize_online
        from commerce_hub.data.quality.online import capture_online,calculation_snapshot
        class Context:
            def check(self):pass
        checks=[]
        for m in mappings:
            reader=TeachingERPReader(erp_config())
            caps,receipt=collect(reader,m,Context(),DATASET+'-'+m.sku)
            projection,verified=observed(caps,m,receipt)
            normalized=normalize_online(caps,m,receipt,verified)
            asset=capture_online(projection,receipt,verified,normalized)
            (self.root/('replenishment-'+m.sku+'.json')).write_bytes(canonical_bytes(dict(captures=caps,asset=asset)))
            valid=calculation_snapshot(asset).calculation_allowed
            checks.append(dict(sku=m.sku,mappingVerified=verified,calculationAllowed=valid,issues=normalized.get('issues',[])))
            check(verified and valid,'REPLENISHMENT_INPUT_NOT_ADMISSIBLE')
        self.journal['replenishmentChecks']=checks;self.save()

    def register(self,mappings):
        from commerce_hub.bootstrap.local_platform import configure
        from commerce_hub.infrastructure.database import Database
        from commerce_hub.data.projection.monitor import MonitorRegistry
        db=Database(configure())
        try:
            registry=MonitorRegistry(db.engine,'s01-owned-teaching-local')
            previous=[m.model_dump(mode='json') for m in registry.mappings() if m.monitor.datasetId!=DATASET]
            digest=registry.activate([m.model_dump(mode='json') for m in mappings],'owner-authorized-erp-simulation-20261116')
            current=registry.mappings()
            check(previous==[m.model_dump(mode='json') for m in current if m.monitor.datasetId!=DATASET],'PREVIOUS_MEMBERSHIP_CHANGED')
            self.journal['registration']=dict(contentDigest=digest,newScopes=3,totalScopes=len(current),previousMembersPreserved=True)
            self.save()
        finally:db.close()

    def verify_after_sales(self):
        from commerce_hub.bootstrap.local_platform import configure
        from commerce_hub.bootstrap.after_sales import source_reader
        reader=source_reader(configure());store=self.journal['members'][0]['store']['store_name']
        inbox=reader.discover(store,lambda:None)
        check(inbox['complete'] and {r['ticketId'] for r in inbox['items']}=={str(t['id']) for t in self.journal['tickets']},'AFTER_SALES_INBOX_COVERAGE_FAILED')
        checks=[]
        for ti in [0,7,10]:
            t=self.journal['tickets'][ti]
            proof=reader.evidence(str(t['id']),store,lambda:None,'simulation-readback-'+str(t['id']))
            check(proof.get('identity') is not None and proof['identity']['sku'] in {p['sku'] for p in profiles()},'CASE_IDENTITY_UNVERIFIED')
            checks.append(dict(ticketId=str(t['id']),identity=proof['identity'],missing=proof['missing']))
        self.journal['afterSalesChecks']=dict(discoveredTickets=len(inbox['items']),identities=checks);self.save()

    def summary(self):
        PUBLIC.mkdir(parents=True,exist_ok=True)
        out=dict(plan=plan(),state=self.journal['state'],sourceNature=NATURE,
            members=[dict(sku=m['product']['sku'],productId=m['product']['id'],storeId=m['store']['id'],warehouseId=m['warehouse']['id'],
                          salesOrders=len(m['sales']),soldQuantity=sum(x['item_list'][0]['quantity'] for x in m['sales']),
                          opening=m['opening'],closing=m['closing']) for m in self.journal['members']],
            ticketIds=[t['id'] for t in self.journal['tickets']],returnDraftIds=[r['id'] for r in self.journal['returns']],
            registration=self.journal.get('registration'),replenishmentChecks=self.journal.get('replenishmentChecks'),
            afterSalesChecks=self.journal.get('afterSalesChecks'),
            calls=self.client.counts,actualModelCalls=0,humanRiskDecisions=0,
            limitations=['TEACHING_ONLY','SHARED_TENANT_NOT_SOURCE_ROW_ISOLATED','RETURN_DRAFTS_NOT_RECEIVED_OR_REFUNDED',
                         'NO_CUSTOMER_MESSAGES_SENT','CURRENT_POSTING_NOT_HISTORICAL_POSTING','NO_PURCHASE_WRITES',
                         'ERP_NATIVE_MATURE_RETURN_COHORT_NOT_VERIFIED','AI_AND_HUMAN_DECISIONS_NOT_PRESEEDED'])
        (PUBLIC/'summary.json').write_bytes(json.dumps(out,ensure_ascii=False,indent=2).encode('utf-8')+b'\n')
        print(json.dumps(dict(state=out['state'],skus=3,sales=30,tickets=12,returnDrafts=7),ensure_ascii=False),flush=True)


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--execute-live',action='store_true')
    args=parser.parse_args()
    if not args.preflight and not args.execute_live:
        print(json.dumps(dict(mode='PLAN_ONLY_NO_NETWORK',**plan()),ensure_ascii=False,indent=2))
    else:
        try:
            importer=Importer()
            importer.execute() if args.execute_live else importer.preflight()
        except Exception as error:
            print(json.dumps(dict(state='STOPPED',error=getattr(error,'code',type(error).__name__),httpStatus=getattr(error,'status',None))),flush=True)
            raise SystemExit(1) from None
