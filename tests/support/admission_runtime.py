"""Synthetic source contracts for runtime admission; no ERP or models."""
from copy import deepcopy
from datetime import datetime,timedelta,timezone
from commerce_hub.data.projection.runtime import evaluate_runtime
from commerce_hub.data.projection.monitor import ForecastPolicy
from tests.unit.data.test_owned import owned_case


def runtime_case(*,day='2026-11-13',quantities=(4,5,4,6,9,5,6),opening=45):
    m,c,r=owned_case(quantities=quantities,opening=opening)
    anchor=day+'T06:00:05+00:00'
    e=dict(entityKey='synthetic-entity',identityVerified=True,productId='1',inventoryIds=['7'],sourceTenant='1',storeId='2',warehouseId='3',
        sku=m.sku,storeName=m.storeName,warehouseName=m.warehouseName,suggestionIds=[])
    inv=deepcopy(c['inventory']);inv['observedAt']=anchor
    ledger=[row for k,v in c.items() if k.startswith('ledger-') for row in v['rows']]
    workflows={str(s['id']):c['workflow-'+str(s['id'])]['rows'][0]['data'] for s in c['sales']['rows']}
    constraints=dict(moq=12,orderMultiple=8,leadDays=2,hardBlocks=[])
    return dict(entity=e,product=c['product']['rows'][0],inventory=inv,movements=dict(rows=ledger,complete=True),
        sales=c['sales']['rows'],workflows=workflows,policy=m.monitor.policy,
        receipt=dict(startedAt=day+'T06:00:00+00:00',completedAt=anchor,businessDate=day),
        constraints=constraints,opening_binding=m,scope_complete=True)


def evaluate(case):return evaluate_runtime(**deepcopy(case))


from tests.support.v2 import SyntheticERP
from urllib.parse import urlsplit,parse_qs
import json


class AdmissionERP(SyntheticERP):
    """Paid/shipped synthetic source through real V2Reader/Handler/O01."""
    def __init__(self):
        super().__init__(0);self.mapping,self.captures,_=owned_case()
        c=self.captures;m=self.mapping
        self.data.update({n:deepcopy(c[k]['rows']) for n,k in [('products','product'),('inventory','inventory'),('stores','store'),
            ('warehouses','warehouse'),('quotes','quotes'),('sales','sales'),('listings','listing')]})
        self.data['products'][0].update(name='Synthetic Product',supplier_name='Synthetic Supplier')
        self.data['inventory'][0].update(store_name=m.storeName,warehouse_name=m.warehouseName)
        self.data['stores'][0]['store_name']=m.storeName;self.data['warehouses'][0]['name']=m.warehouseName
        self.data['quotes'][0].update(currency='USD',supplier_name='Synthetic Supplier')
        self.ledger=[deepcopy(r) for k,v in c.items() if k.startswith('ledger-') for r in v['rows']]
        self.workflows={str(s['id']):deepcopy(c['workflow-'+str(s['id'])]['rows'][0]) for s in c['sales']['rows']}
    def transport(self,method,target,headers,body,config):
        path=urlsplit(target).path;params={k:v[0] for k,v in parse_qs(urlsplit(target).query).items()}
        if path=='/api/v1/stock/ledger':
            self.calls.append((method,path,params));rows=[r for r in self.ledger if not params.get('sku') or r['sku']==params['sku']]
            return 200,json.dumps(dict(items=rows,total=len(rows))).encode()
        if path.startswith('/api/v1/sales-workflow/'):
            self.calls.append((method,path,params));return 200,json.dumps(self.workflows[path.rsplit('/',1)[1]]).encode()
        return super().transport(method,target,headers,body,config)
