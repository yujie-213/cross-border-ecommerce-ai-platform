"""Warehouse projection only; these fixtures do not assert live ERP acceptance."""
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from commerce_hub.scenarios.after_sales.source import SourceReader


def setup(tmp_path):
    member=NS(sku='S',sourceTenant='1',sourceStore='2',sourceWarehouse='3',warehouseName='WH',storeName='Store',
        monitor=NS(productId='4',salesIds=['5'],inventoryIds=['6']))
    s=SourceReader(None,{'Store':dict(sourceTenant='1',storeId='2')},tmp_path,owned_provider=lambda:[member])
    s.verify_mapping=lambda identity,check:dict(independentReadback=True,relationVerified=True,observedAt='2026-11-16T00:00:00Z')
    order=dict(id=5,shipping_warehouse='WH',item_list=[dict(sku='S',quantity=2)])
    identity=dict(sku='S',productId='4',storeId='2',sourceTenant='1')
    workflow=dict(local_only=True,order_id=5,state='shipped',shipments=[dict(order_id=5,outbound_id=7)])
    row=dict(id=8,resource='outbound-orders',record_id=7,inventory_id=6,sku='S',warehouse_name='WH',operation='post',
             reverses_id=None,delta_quantity=-2,delta_available=-2,before_quantity=10,after_quantity=8,before_available=10,after_available=8)
    reader=NS(read=lambda *args,**kwargs:NS(complete=True,records=[row]))
    return s,reader,order,identity,workflow,row,member


def test_registered_id_and_real_ledger_chain_resolves_warehouse(tmp_path):
    s,r,o,i,w,row,m=setup(tmp_path)
    proof=s.order_warehouse(r,'Store',o,i,w,lambda:None)
    assert proof['warehouseId']=='3' and proof['ledgerEventIds']==[8] and proof['inventoryIds']==['6']


@pytest.mark.parametrize('change',[
    dict(inventory_id=999),dict(warehouse_name='Other'),dict(record_id=999),dict(resource='inbound-orders'),
    dict(reverses_id=12),dict(delta_available=-1),dict(after_quantity=9),dict(operation='reverse')])
def test_foreign_reversed_or_inconsistent_posting_stays_unknown(tmp_path,change):
    s,r,o,i,w,row,m=setup(tmp_path);row.update(change)
    assert s.order_warehouse(r,'Store',o,i,w,lambda:None) is None


def test_name_without_registered_inventory_is_not_a_proof(tmp_path):
    s,r,o,i,w,row,m=setup(tmp_path);m.monitor.inventoryIds=[]
    assert s.order_warehouse(r,'Store',o,i,w,lambda:None) is None


def test_duplicate_ledger_and_incomplete_page_are_not_a_proof(tmp_path):
    s,r,o,i,w,row,m=setup(tmp_path)
    r.read=lambda *a,**k:NS(complete=True,records=[row,deepcopy(row)])
    assert s.order_warehouse(r,'Store',o,i,w,lambda:None) is None
    r.read=lambda *a,**k:NS(complete=False,records=[row])
    assert s.order_warehouse(r,'Store',o,i,w,lambda:None) is None


def test_shared_name_with_ambiguous_membership_stays_unknown(tmp_path):
    s,r,o,i,w,row,m=setup(tmp_path);other=deepcopy(m);other.sourceWarehouse='99'
    s.owned_provider=lambda:[m,other]
    assert s.order_warehouse(r,'Store',o,i,w,lambda:None) is None


def test_unpaid_and_nonlocal_orders_stay_unknown(tmp_path):
    s,r,o,i,w,row,m=setup(tmp_path)
    assert s.order_warehouse(r,'Store',o,i,w|dict(local_only=False),lambda:None) is None
    assert s.order_warehouse(r,'Store',o,i,w|dict(state='unpaid'),lambda:None) is None
