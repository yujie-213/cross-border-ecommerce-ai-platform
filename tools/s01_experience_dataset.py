"""Explicit, resumable teaching-only import for the authorized S01 experience batch.

No purchase writes, approvals, receiving, external notifications or ERP database access.
All requests use deterministic business keys; uncertain writes are read back, never resent.
Raw business responses and the durable journal stay in the ignored private directory.
"""
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
import argparse
import hashlib
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from dotenv import dotenv_values
from tools.s01_teaching_dataset import TeachingDatasetClient, Config, DatasetError, canonical_bytes

BATCH='HLX-S01-20261114'
DATASET='hailan-s01-experience-20261114'
PRIVATE=ROOT/'data/private/s01-experience-20261114'
NATURE='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'
COLLECTIONS={'products','inventory','listings','store-authorizations','warehouses','suppliers','supplier-quotes','sales-orders','replenishment'}

def scenarios():
    days=[(date(2026,11,7)+timedelta(days=i)).isoformat() for i in range(7)]
    old=[(date(2026,10,28)+timedelta(days=i)).isoformat() for i in range(7)]
    specs=[
      ('USB-STABLE','编织充电线 · 稳定缺货',days,[5]*7,6,'稳定销售，主仓需补，另一店仓库存充足'),
      ('TOTE-SAFE','帆布收纳袋 · 库存充足',days,[4]*7,180,'稳定销售，暂不补货'),
      ('LAMP-SURGE','阅读灯 · 近期上升',days,[2,2,3,4,8,12,16],8,'近期明显上升；参考均值可能低估，优先核实加急'),
      ('CUP-SLOW','随行杯 · 销量下降',old,[8,6,4,3,2,1,1],60,'销量下降且样本陈旧，仍保留参考判断'),
      ('MAT-SPARSE','桌垫 · 间歇销售',['2026-11-01','2026-11-05','2026-11-09','2026-11-12'],[3,4,2,3],4,'不连续样本，未知日不补零，披露保守试算'),
      ('STAND-NEW','折叠支架 · 新品',['2026-11-13'],[2],1,'仅一个销售日，低可信度参考'),
      ('CASE-NOQUOTE','数码收纳包 · 缺采购条件',days,[4]*7,3,'缺有效报价及供应商关系，仍预测与计算参考补充'),
      ('HUB-PENDING','扩展坞 · 销量待核实',[],[],10,'只有未支付未发货订单，不能推断有效销量'),
    ]
    return [dict(sku='HLX-'+k,name=n,days=d,quantities=q,available=a,scene=s) for k,n,d,q,a,s in specs]

class Client(TeachingDatasetClient):
    def __init__(self):
        v=dotenv_values(ROOT/'.env.erp',interpolate=False)
        super().__init__(Config(v.get('ERP_USERNAME') or '',v.get('ERP_PASSWORD') or '',v.get('ERP_ACCESS_TOKEN') or '',timeout=15),PRIVATE/'raw')
        self.events=[]
    def authenticate(self):
        if self.token:return
        status,raw=self._transport('POST','/api/auth-server/oauth/access-token',{'Content-Type':'application/json'},canonical_bytes(dict(appId=self.config.username,appSecret=self.config.password)))
        if status!=200:raise DatasetError('AUTH_REJECTED',status)
        self.token=json.loads(raw).get('data',{}).get('access_token')
        if not isinstance(self.token,str) or not self.token or '\n' in self.token or '\r' in self.token:raise DatasetError('AUTH_INVALID')
        # Never persist authentication responses or reusable session credentials.
    def _allow(self,method,path,*,auth):
        if method=='GET' and (path in {'/api/v1/me','/api/v1/data-contract','/api/v1/stock/ledger'} or path.startswith('/api/v1/sales-workflow/')):return
        parts=path.split('/')
        if method=='GET' and len(parts) in {4,5} and parts[3] in COLLECTIONS:return
        if method=='POST' and len(parts)==4 and parts[3] in COLLECTIONS:return
        if method=='POST' and len(parts)==6 and parts[3]=='sales-workflow' and parts[5] in {'record-payment','ship'} and parts[4] in getattr(self,'owned_sales',set()):return
        raise DatasetError('EXPERIENCE_OPERATION_NOT_ALLOWED')
    def request(self,method,path,values=None,**kwargs):
        time.sleep(.3)
        try:
            try:r,sha,at,ref=super().request(method,path,values,**kwargs)
            except DatasetError as e:
                if method!='GET' or e.status not in {502,503,504}:raise
                time.sleep(1)
                r,sha,at,ref=super().request(method,path,values,**kwargs)
            self.events.append(dict(method=method,path=path,status='OK',sha256=sha,rawRef=ref,at=at))
            return r
        finally:
            with (PRIVATE/'requests.jsonl').open('a',encoding='utf-8') as f:
                f.write(json.dumps(dict(method=method,path=path,at=datetime.now(timezone.utc).isoformat()))+'\n')
    def lookup(self,resource,key,value):
        params=dict(quote_no=value) if resource=='supplier-quotes' else dict(field=key,q=value,match='exact')
        r=self.request('GET','/api/v1/'+resource,dict(params,offset=0,limit=20,**({'view':'full'} if resource in {'inventory','sales-orders'} else {})))
        rows=r.get('items');total=r.get('total')
        if not isinstance(rows,list) or total!=len(rows) or total>1 or any(str(x.get(key))!=value or (str(x.get('tenant_id'))!='1' and resource!='supplier-quotes') for x in rows):raise DatasetError('EXACT_LOOKUP_INCOMPLETE_OR_FOREIGN')
        return rows

class Importer:
    def __init__(self):
        PRIVATE.mkdir(parents=True,exist_ok=True)
        self.client=Client();self.path=PRIVATE/'journal-experience.json'
        self.journal=json.loads(self.path.read_bytes()) if self.path.exists() else dict(batch=BATCH,sourceNature=NATURE,operations={},members=[])
        if self.journal['batch']!=BATCH:raise DatasetError('JOURNAL_BATCH_CONFLICT')
    def save(self):
        temp=self.path.with_suffix('.part');temp.write_bytes(canonical_bytes(self.journal));temp.replace(self.path)
    def create(self,resource,key,value,payload):
        op=resource+':'+value;fp=hashlib.sha256(canonical_bytes(payload)).hexdigest();prior=self.journal['operations'].get(op)
        if prior and prior['fingerprint']!=fp:raise DatasetError('IMPORT_PAYLOAD_CHANGED')
        found=self.client.lookup(resource,key,value)
        if found:
            if not prior:raise DatasetError('EXISTING_RESOURCE_NOT_OWNED')
            actual=found[0]
        elif prior:
            raise DatasetError('UNKNOWN_WRITE_NOT_FOUND_DO_NOT_RESEND')
        else:
            self.journal['operations'][op]=dict(state='SENDING',resource=resource,businessKey=value,payload=payload,fingerprint=fp);self.save()
            try:self.client.request('POST','/api/v1/'+resource,payload)
            except Exception:
                self.journal['operations'][op]['state']='UNKNOWN';self.save();raise
            found=self.client.lookup(resource,key,value)
            if len(found)!=1:raise DatasetError('INDEPENDENT_READBACK_MISSING')
            actual=found[0]
        ignored={'expected_version','request_key','supplier_code'} if resource=='supplier-quotes' else set()
        if resource=='inventory' and prior and prior['state']=='VERIFIED':ignored|={'quantity','available'}
        for k,v in payload.items():
            if k in ignored:continue
            if str(actual.get(k))!=str(v) and actual.get(k)!=v:raise DatasetError('READBACK_PAYLOAD_MISMATCH_'+resource+'_'+k)
        self.journal['operations'][op].update(state='VERIFIED',erpId=str(actual['id']),record=actual);self.save()
        print(json.dumps(dict(verified=resource,key=value,id=actual['id'])),flush=True)
        return actual
    def workflow(self,sale,action,payload):
        sid=str(sale['id']);self.client.owned_sales=getattr(self.client,'owned_sales',set())|{sid}
        op='sales-workflow:'+sid+':'+action;fp=hashlib.sha256(canonical_bytes(payload)).hexdigest();prior=self.journal['operations'].get(op)
        if prior:
            if prior['fingerprint']!=fp:raise DatasetError('WORKFLOW_PAYLOAD_CHANGED')
            if prior['state']=='VERIFIED':return
            wf=self.client.request('GET','/api/v1/sales-workflow/'+sid);data=wf.get('data',{})
            matches=(data.get('payment_reference')==payload.get('reference') and data.get('paid_amount')==payload.get('amount') and data.get('currency')==payload.get('currency')) if action=='record-payment' else any(s.get('tracking_no')==payload.get('tracking_no') and s.get('carrier')==payload.get('carrier') for s in data.get('shipments',[]))
            if data.get('local_only') is not True:raise DatasetError('LOCAL_ONLY_WORKFLOW_REQUIRED')
            if not matches:
                # The documented FULL-order shipment is idempotent. After an exact
                # read proves no shipment, allow ONE replay of the identical command.
                if action!='ship' or data.get('shipments') or data.get('outbound_id') or prior.get('recoveryReplayCount',0)>=1:
                    raise DatasetError('UNKNOWN_WORKFLOW_REQUIRES_ORIGINAL_REFERENCE_READBACK')
                prior['recoveryReplayCount']=1;prior['replayAfterExactEmptyRead']=True;self.save()
                self.client.request('POST','/api/v1/sales-workflow/'+sid+'/'+action,payload)
                wf=self.client.request('GET','/api/v1/sales-workflow/'+sid);data=wf.get('data',{})
                if not any(s.get('tracking_no')==payload.get('tracking_no') and s.get('carrier')==payload.get('carrier') for s in data.get('shipments',[])):raise DatasetError('SHIPMENT_REPLAY_UNCONFIRMED')
            self.journal['operations'][op].update(state='VERIFIED',workflow=wf,recoveredByReadOnly=True);self.save();return
        # Validate that the endpoint represents internal simulation before sending.
        wf=self.client.request('GET','/api/v1/sales-workflow/'+sid)
        if wf.get('data',{}).get('local_only') is not True:raise DatasetError('LOCAL_ONLY_WORKFLOW_REQUIRED')
        self.journal['operations'][op]=dict(state='SENDING',fingerprint=fp,payload=payload,saleId=sid);self.save()
        try:
            receipt=self.client.request('POST','/api/v1/sales-workflow/'+sid+'/'+action,payload)
            wf=self.client.request('GET','/api/v1/sales-workflow/'+sid)
            current=self.client.request('GET','/api/v1/sales-orders/'+sid)
            record=current.get('data',current)
            field='payment_status' if action=='record-payment' else 'fulfillment_status';expected='已支付' if action=='record-payment' else '已发货'
            if record.get(field)!=expected:raise DatasetError('WORKFLOW_STATE_READBACK_MISMATCH')
            self.journal['operations'][op].update(state='VERIFIED',workflow=wf,record=record,receipt=receipt);self.save()
        except Exception:
            self.journal['operations'][op]['state']='UNKNOWN';self.save();raise
    def preflight(self):
        me=self.client.request('GET','/api/v1/me');me=me.get('data',me)
        if str(me.get('tenant_id'))!='1' or '*' not in me.get('permissions',[]):raise DatasetError('TEACHING_SCOPE_NOT_AUTHORIZED')
        contract=self.client.request('GET','/api/v1/data-contract')
        if contract.get('kind')!='synthetic':raise DatasetError('TEACHING_SOURCE_REQUIRED')
        schema=json.loads((ROOT/'docs/ERP-openapi.yaml').read_bytes())
        for path in ['/api/v1/sales-workflow/{id}/record-payment','/api/v1/sales-workflow/{id}/ship']:
            if 'post' not in schema['paths'].get(path,{}):raise DatasetError('LOCAL_WORKFLOW_CONTRACT_MISSING')
        self.journal['preflight']=dict(at=datetime.now(timezone.utc).isoformat(),tenant='1',contractDigest=hashlib.sha256(canonical_bytes(contract)).hexdigest(),externalActions=False)
        self.save();return schema
    def execute(self):
        if self.journal.get('enrichment'):
            from tools.s01_experience_finalize import Finalizer
            return Finalizer().execute()
        self.preflight()
        stores=[self.create('store-authorizations','store_name',BATCH+'-'+c,dict(store_name=BATCH+'-'+c,platform='Amazon',site='US',status_text='已授权',fee_rate=0)) for c in ['EAST','WEST']]
        warehouses=[self.create('warehouses','warehouse_code',BATCH+'-'+c,dict(warehouse_code=BATCH+'-'+c,name='海岚体验'+n+'仓',warehouse_type='自营仓',country='US',status_text='正常')) for c,n in [('EAST','东部'),('WEST','西部')]]
        supplier=self.create('suppliers','supplier_code',BATCH+'-SUP',dict(supplier_code=BATCH+'-SUP',name='海岚体验教学供应商',status_text='正常',purchase_user='教学运营'))
        members=[];products={};quotes={};groups={};inventory_records={};listings={}
        for index,s in enumerate(scenarios()):
            sku=s['sku'];noquote='NOQUOTE' in sku
            product=self.create('products','sku',sku,dict(sku=sku,name=s['name'],category='S01受控体验',status='ACTIVE',unit='piece',price=10,cost=4,default_carton_qty=4,
                tag=BATCH,owner='CommerceHub',description=NATURE+';'+DATASET+';'+s['scene'],supplier_name=None if noquote else supplier['name']))
            products[sku]=product
            quote=self.create('supplier-quotes','quote_no',BATCH+'-Q-'+str(index+1),dict(quote_no=BATCH+'-Q-'+str(index+1),supplier_code=supplier['supplier_code'],sku=sku,currency='USD',unit_price='4.00',minimum_quantity=8,lead_days=2,valid_from='2026-11-01',valid_to='2027-11-14',enabled=not noquote,expected_version=0,request_key=BATCH+'-QUOTE-'+str(index+1)))
            quotes[sku]=quote
            if str(quote.get('supplier_id'))!=str(supplier['id']) or str(quote.get('product_id'))!=str(product['id']):raise DatasetError('QUOTE_PARENT_RELATION_MISMATCH')
            for scope_index in ([0,1] if index==0 else [0]):
                st,wh=stores[scope_index],warehouses[scope_index];available=120 if scope_index else s['available'];total=sum(s['quantities']);initial=available+total
                inv=self.create('inventory','batch_no',BATCH+'-I-'+str(index+1)+'-'+str(scope_index),dict(batch_no=BATCH+'-I-'+str(index+1)+'-'+str(scope_index),wid=wh['id'],warehouse_name=wh['name'],product_id=product['id'],sku=sku,store_id=st['id'],store_name=st['store_name'],quantity=initial,available=initial,source_batch_no=BATCH,order_sn=BATCH+'-OPEN-'+str(index+1)+'-'+str(scope_index)))
                inventory_records[(sku,scope_index)]=inv
                listing=self.create('listings','listing_id',BATCH+'-L-'+str(index+1)+'-'+str(scope_index),dict(sku=sku,platform='Amazon',store_name=st['store_name'],listing_id=BATCH+'-L-'+str(index+1)+'-'+str(scope_index),title=s['name'],price=10,stock=initial,status_text='在售'))
                listings[(sku,scope_index)]=listing
                for day,qty in zip(s['days'],s['quantities']):groups.setdefault((scope_index,day),[]).append(dict(sku=sku,product_id=product['id'],quantity=qty,unit_price=10,amount=qty*10))
                members.append(dict(scenario=s,scopeIndex=scope_index,store=st,warehouse=wh,product=product,quote=quote,inventory=inv,listing=listing,initial=initial,expectedAvailable=available,salesIds=[]))
        for (scope_index,day),lines in sorted(groups.items()):
            number=BATCH+'-S-'+str(scope_index)+'-'+day.replace('-','');st=stores[scope_index];wh=warehouses[scope_index];amount=sum(x['amount'] for x in lines)
            sale=self.create('sales-orders','order_sn',number,dict(order_sn=number,platform='Amazon',store_name=st['store_name'],site='US',country='US',order_time=day+' 12:00:00',currency='USD',amount=amount,shipping_warehouse=wh['name'],remark=NATURE+';'+BATCH,item_list=lines))
            self.workflow(sale,'record-payment',dict(reference=number+'-PAY',amount=f'{amount:.2f}',currency='USD'))
            self.workflow(sale,'ship',dict(carrier='TEACHING_LOCAL_ONLY',tracking_no=number+'-SHIP'))
            for m in members:
                if m['scopeIndex']==scope_index and any(l['sku']==m['product']['sku'] for l in lines):m['salesIds'].append(str(sale['id']))
        missing=next(m for m in members if 'PENDING' in m['product']['sku']);number=BATCH+'-UNPAID'
        sale=self.create('sales-orders','order_sn',number,dict(order_sn=number,platform='Amazon',store_name=missing['store']['store_name'],site='US',country='US',order_time='2026-11-13 12:00:00',currency='USD',amount=20,shipping_warehouse=missing['warehouse']['name'],remark=NATURE+';UNPAID_HISTORY_NOT_DEMAND',item_list=[dict(sku=missing['product']['sku'],product_id=missing['product']['id'],quantity=2,unit_price=10,amount=20)]))
        missing['salesIds']=[str(sale['id'])]
        for sku,qty,si in [('HLX-USB-STABLE',16,0),('HLX-TOTE-SAFE',0,0),('HLX-USB-STABLE',0,1)]:
            self.create('replenishment','recommendation_no',BATCH+'-R-'+sku+'-'+str(si),dict(recommendation_no=BATCH+'-R-'+sku+'-'+str(si),sku=sku,store_name=stores[si]['store_name'],suggested_qty=qty,status_text='教学人工预置',generated_at='2026-11-14',replenishment_mode='SIMULATED_MANUAL_REFERENCE'))
        from tools.s01_experience_finalize import Finalizer
        return Finalizer().execute()
    def register(self,members):
        from commerce_hub.bootstrap.local_platform import configure
        from commerce_hub.infrastructure.database import Database
        from commerce_hub.data.projection.monitor import MonitorRegistry
        from commerce_hub.data.sync.online import OnlineMapping
        maps=[]
        for m in members:
            sku=m['product']['sku'];sid=str(m['store']['id']);wid=str(m['warehouse']['id'])
            scope=dict(tenantId='s01-owned-teaching-local',storeIds=[sid],warehouseIds=[wid],canonicalSkuIds=[sku],fields=['quantity'])
            binding=dict(datasetId=DATASET,scopeVersion=1,importBatchId=BATCH,productId=str(m['product']['id']),listingId=str(m['listing']['id']),supplierId=str(m['quote']['supplier_id']),quoteId=str(m['quote']['id']),quoteNo=m['quote']['quote_no'],inventoryIds=[str(m['inventory']['id'])],salesIds=m['salesIds'],purchaseIds=[],openingQuantity=str(m['initial']),evidenceDigest=hashlib.sha256(canonical_bytes(m)).hexdigest())
            maps.append(OnlineMapping(scope=scope,sku=sku,sourceTenant='1',sourceStore=sid,sourceWarehouse=wid,storeName=m['store']['store_name'],warehouseName=m['warehouse']['name'],monitor=binding).validate_scope().model_dump(mode='json'))
        db=Database(configure())
        try:digest=MonitorRegistry(db.engine,'s01-owned-teaching-local').activate(maps,'owner-authorized-experience-import')
        finally:db.close()
        self.journal['registration']=dict(datasetId=DATASET,scopeVersion=1,contentDigest=digest,memberCount=len(maps));self.journal['state']='ACTIVE';self.save()
        print(json.dumps(dict(status='ACTIVE',newSkus=len(scenarios()),newScopes=len(maps),existingDataPreserved=True)),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute-live',action='store_true');args=p.parse_args()
    if not args.execute_live:
        print(json.dumps(dict(batch=BATCH,scenarios=scenarios(),plannedNewSkus=8,plannedScopes=9,mode='PLAN_ONLY_NO_NETWORK'),ensure_ascii=False));raise SystemExit(0)
    if datetime.now(timezone.utc).date()!=date(2026,11,14):raise SystemExit('EXPLICIT_BATCH_DAY_REQUIRED')
    try:Importer().execute()
    except Exception as e:
        print(json.dumps(dict(status='STOPPED',error=e.code if isinstance(e,DatasetError) else type(e).__name__,httpStatus=getattr(e,'status',None))),flush=True);raise SystemExit(1) from None
