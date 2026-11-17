"""Synthetic ERP cohort fixture; never used by the application launcher."""
from datetime import datetime,timezone
from types import SimpleNamespace

from commerce_hub.adapters.erp import ReadBatch
from commerce_hub.scenarios.after_sales.source import SourceReader


class ReturnERP:
    def __init__(self):
        self.orders=[];self.returns=[];self.reviews=[]
        for period,first in [('previous',1),('current',26)]:
            day='2026-11-08' if period=='previous' else '2026-11-15'
            for n in range(first,first+25):
                self.orders.append(dict(id=n,tenant_id=1,store_name='Owned Store',order_sn=f'ORDER-{n}',
                    order_time=day+'T10:00:00+08:00',fulfillment_status='shipped',shipping_warehouse='WH-A',
                    item_list=[dict(sku='SKU-KNIT',quantity=1)]))
        for n,order_id in enumerate([1,26,27,28,29,30,31],start=1):
            self.returns.append(dict(id=900+n,return_no=f'RET-{n}',order_id=order_id,reason='接缝处开线',
                item_list=[dict(sku='SKU-KNIT',quantity=1)],state='received',created_at='2026-11-17T10:00:00+08:00',
                authorized_at='2026-11-17T09:00:00+08:00',received_at='2026-11-17T10:00:00+08:00',refunded_at=None,quality_list=[]))
        for n in range(1,3):
            self.reviews.append(dict(id=n,store_id=2,store_name='Owned Store',sku='SKU-KNIT',rating=2,
                body='缝线松脱',title='做工反馈',business_date='2026-11-08',platform='Amazon'))
        for n in range(3,9):
            self.reviews.append(dict(id=n,store_id=2,store_name='Owned Store',sku='SKU-KNIT',rating=1,
                body='缝线松脱',title='做工反馈',business_date='2026-11-15',platform='Amazon'))

    def batch(self,rows):
        return ReadBatch(tuple(rows),True,1,len(rows),datetime.now(timezone.utc).isoformat(),'0'*64)

    def read(self,path,params,**kwargs):
        if path=='/api/v1/sales-orders':
            ids=set(params['ids'].split(','));return self.batch([r for r in self.orders if str(r['id']) in ids])
        if path=='/api/v1/sales-returns':
            return self.batch([r for r in self.returns if r['order_id']==params['order_id']])
        if path=='/api/v1/customer-voice':return self.batch(self.reviews)
        if path=='/api/v1/products':return self.batch([dict(id=10,tenant_id=1,sku='SKU-KNIT',name='澄屿针织衫',category='APPAREL')])
        raise AssertionError(path)

    def detail(self,resource,record_id):
        return dict(data=next(r for r in self.returns if str(r['id'])==str(record_id)))

