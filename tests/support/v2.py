"""Entirely synthetic source; can add SKU without any application-code/ID-list edit."""
from copy import deepcopy
from datetime import datetime,timezone
from urllib.parse import urlsplit,parse_qs
import json
from commerce_hub.adapters.erp import ERPConfig,AUTH_PATH
from commerce_hub.data.sync.v2 import V2Reader


class MemoryCheckpoint:
    def __init__(self):self.value=dict(requestCount=0)
    def load(self):return deepcopy(self.value)
    def save(self,value):self.value=deepcopy(value)


class SyntheticERP:
    def __init__(self,count=5):
        self.data=dict(stores=[dict(id=1,tenant_id=1,store_name='Synthetic Store')],warehouses=[dict(id=1,tenant_id=1,name='Synthetic Warehouse')],
            products=[],inventory=[],suggestions=[],quotes=[],listings=[],sales=[],formalPurchases=[])
        self.calls=[];self.mutations=0;self.orders={};self.lost_create=False;self.fail_resource=None
        for i in range(count):self.add(i)
    def add(self,i):
        sku='V2-SKU-'+str(i);pid=i+1
        self.data['products'].append(dict(id=pid,tenant_id=1,sku=sku,name='Synthetic Product '+str(i),unit='piece',default_carton_qty=8,supplier_name='Synthetic Supplier'))
        self.data['inventory'].append(dict(id=pid+10000,tenant_id=1,product_id=pid,sku=sku,store_id=1,store_name='Synthetic Store',wid=1,warehouse_name='Synthetic Warehouse',quantity=0,available=0))
        self.data['suggestions'].append(dict(id=pid+20000,tenant_id=1,sku=sku,store_name='Synthetic Store',suggested_qty=120,daily_sales=5,
            recommendation_no='SYN-REC-'+str(pid),urgency='最急',stockout_date='2026-11-14',created_at='2026-11-13T04:00:00Z',updated_at='2026-11-13T04:00:00Z',generated_at='2026-11-14'))
        self.data['quotes'].append(dict(id=pid+30000,product_id=pid,supplier_id=5,supplier_name='Synthetic Supplier',sku=sku,enabled=True,status='effective',
            quote_no='SYN-QUOTE-'+str(pid),valid_from='2020-01-01',valid_to='2099-12-31',minimum_quantity=12,minimum_amount='0',unit_price='2.40',currency='USD',lead_days=2,version=1))
    def transport(self,method,target,headers,body,config):
        path=urlsplit(target).path;params={k:v[0] for k,v in parse_qs(urlsplit(target).query).items()}
        self.calls.append((method,path,deepcopy(params)))
        def out(value,status=200):return status,json.dumps(value,ensure_ascii=False).encode()
        if path==AUTH_PATH:return out(dict(data=dict(access_token='synthetic-source-token')))
        if method=='POST':
            self.mutations+=1
            if path=='/api/v1/purchase-orders':
                p=json.loads(body);row=dict(p,id=90001,tenant_id=1,status_text='待提交',received_qty=0)
                self.orders[p['order_sn']]=row
                if self.lost_create:raise TimeoutError()
                return out(row,201)
            if path=='/api/v1/workflows/purchase-orders/90001/submit':
                next(iter(self.orders.values()))['status_text']='待审核';return out(dict(code=0))
            raise AssertionError('Unexpected synthetic mutation')
        if path=='/api/v1/me':return out(dict(tenant_id=1,role='synthetic-test'))
        if path=='/api/v1/suppliers/5':return out(dict(id=5,tenant_id=1,name='Synthetic Supplier'))
        if path=='/api/v1/purchase-orders/90001':return out(next(iter(self.orders.values())))
        resource=path.split('/')[-1]
        if resource==self.fail_resource:return out(dict(error='simulated service unavailable'),503)
        aliases={'store-authorizations':'stores','warehouses':'warehouses','products':'products','inventory':'inventory',
            'replenishment':'suggestions','supplier-quotes':'quotes','listings':'listings','sales-orders':'sales','purchase-orders':'formalPurchases'}
        rows=deepcopy(self.data[aliases[resource]])
        if resource=='purchase-orders' and params.get('field')=='order_sn':rows=[deepcopy(x) for x in self.orders.values()]
        if params.get('field') and params.get('q'):
            rows=[r for r in rows if str(r.get(params['field']))==params['q']]
        for key in ['sku','store_id','store_name','warehouse_name']:
            if key in params:rows=[r for r in rows if str(r.get(key))==params[key]]
        if params.get('ids'):rows=[r for r in rows if str(r['id']) in params['ids'].split(',')]
        total=len(rows);offset=int(params.get('offset',0));limit=int(params.get('limit',200))
        return out(dict(items=rows[offset:offset+limit],total=total))
    def reader(self,root,checkpoint=None,check=lambda:None,**kwargs):
        reader=V2Reader(ERPConfig(access_token='synthetic-source-token'),root,checkpoint or MemoryCheckpoint(),check,
            transport=self.transport,sleeper=lambda _:None,**kwargs)
        if getattr(self,'legacy_runtime',False):
            reader.state.pop('decisionVersion',None);reader.checkpoint.save(reader.state)
        return reader
