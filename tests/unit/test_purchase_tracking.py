from types import SimpleNamespace
import pytest
from commerce_hub.adapters.erp import ERPError
from commerce_hub.scenarios.s01_v2.tracking import track_purchases


def sample():
    item=dict(entityKey='one',sku='owned',productId='10',warehouseName='owned-warehouse',
        pendingPurchases=[dict(erpId='2',erpNumber='P-2',status='待审核')])
    policy=SimpleNamespace(source_tenant='1',opening_binding=lambda _: object())
    return item, policy


def test_tracking_reads_current_erp_state_instead_of_snapshot():
    item,policy=sample()
    class Reader:
        def detail(self,resource,key):
            assert (resource,key)==('purchase-orders','2')
            return dict(data=dict(id=2,tenant_id=1,order_sn='P-2',warehouse_name='owned-warehouse',
                status_text='待下单',item_list=[dict(sku='owned',product_id=10,quantity=8)]))
    result=track_purchases([item],policy,Reader())
    row=result['items'][0]
    assert row['verified'] and row['status']=='待下单' and row['previousStatus']=='待审核'
    assert item['pendingPurchases'][0]['status']=='待审核' and result['businessWrites']==0


@pytest.mark.parametrize('discover', [False, True])
@pytest.mark.parametrize('related_first', [False, True])
def test_tracking_does_not_bind_another_warehouses_contextual_purchase(discover, related_first):
    item,policy=sample()
    purchase=dict(erpId='2',erpNumber='P-2',status='待到货',
        warehouseName='owned-warehouse',warehouseMatch=True)
    item.update(pendingPurchases=[],formalPurchases=[purchase])
    related=dict(item,entityKey='other-warehouse',warehouseName='other-warehouse',
        formalPurchases=[dict(purchase,warehouseMatch=False)])
    calls=[]
    current=dict(id=2,tenant_id=1,order_sn='P-2',warehouse_name='owned-warehouse',
        status_text='待到货',item_list=[dict(sku='owned',product_id=10,quantity=48)])
    class Reader:
        def read(self,path,params,**limits):
            return SimpleNamespace(complete=True,records=[current] if params['warehouse_name']=='owned-warehouse' else [])
        def detail(self,resource,key):
            calls.append((resource,key))
            return dict(data=current)
    result=track_purchases([related,item] if related_first else [item,related],policy,Reader(),discover=discover)
    assert result['failedCount']==0 and len(result['items'])==1
    row=result['items'][0]
    assert row['verified'] and row['status']=='待到货' and row['warehouseName']=='owned-warehouse'
    assert row['quantities']==[dict(sku='owned',ordered=48,received=None,pending=None)]
    assert calls==[('purchase-orders','2')]
    assert related['formalPurchases'][0]['warehouseMatch'] is False


def test_tracking_still_rejects_a_purchase_moved_from_its_bound_warehouse():
    item,policy=sample()
    class Reader:
        def detail(self,*args):
            return dict(id=2,tenant_id=1,order_sn='P-2',warehouse_name='other-warehouse',
                status_text='待到货',item_list=[dict(sku='owned',product_id=10,quantity=48)])
    result=track_purchases([item],policy,Reader())
    assert result['failedCount']==1
    assert result['items'][0]['error']=='PURCHASE_TRACKING_RELATION_CHANGED'


def test_tracking_failure_does_not_claim_old_status_is_current_or_drop_record():
    item,policy=sample()
    class Reader:
        def detail(self,*args):raise ERPError('ERP_AUTH_REJECTED')
    result=track_purchases([item],policy,Reader())
    assert result['failedCount']==1
    assert result['items'][0]['status'] is None and result['items'][0]['previousStatus']=='待审核'


def test_tracking_exact_404_is_a_verified_missing_record_not_a_permanent_read_failure():
    item,policy=sample()
    class Reader:
        def detail(self,*args):raise ERPError('ERP_HTTP_ERROR',404)
    result=track_purchases([item],policy,Reader())
    row=result['items'][0]
    assert result['failedCount']==0 and row['verified']
    assert row['status']=='ERP 已无此单' and row['resolution']=='ERP_RECORD_NOT_FOUND'
    assert row['previousStatus']=='待审核' and row['error'] is None


def test_tracking_uses_verified_discovery_status_when_voided_detail_is_no_longer_readable():
    item,policy=sample()
    class Reader:
        def read(self,*args,**kwargs):
            return SimpleNamespace(complete=True,records=[dict(id=2,tenant_id=1,order_sn='P-2',warehouse_name='owned-warehouse',
                status_text='已作废',item_list=[dict(sku='owned',product_id=10,quantity=8)])])
        def detail(self,*args):raise ERPError('ERP_HTTP_ERROR',404)
    result=track_purchases([item],policy,Reader(),discover=True)
    row=result['items'][0]
    assert result['failedCount']==0 and row['verified'] and row['status']=='已作废'
    assert row['quantities']==[dict(sku='owned',ordered=8,received=None,pending=None)]


def test_tracking_refuses_changed_ownership_and_excludes_unregistered_members():
    item,policy=sample()
    class Reader:
        def detail(self,*args):return dict(id=2,tenant_id=99)
    result=track_purchases([item],policy,Reader())
    assert result['items'][0]['error']=='PURCHASE_TRACKING_RELATION_CHANGED'
    policy.opening_binding=lambda _:None
    assert track_purchases([item],policy,Reader())['items']==[]


def test_discovery_finds_new_purchase_for_another_registered_sku_without_snapshot_reference():
    first,policy=sample()
    second=dict(entityKey='two',sku='second',productId='20',warehouseName='owned-warehouse')
    class Reader:
        def read(self,path,params,**limits):
            assert path=='/api/v1/purchase-orders' and params==dict(warehouse_name='owned-warehouse')
            assert limits==dict(page_size=50,max_pages=2)
            return SimpleNamespace(complete=True,records=[dict(id=3,tenant_id=1,order_sn='P-3',warehouse_name='owned-warehouse',
                status_text='待审核',item_list=[dict(sku='second',product_id=20,quantity=16)])])
        def detail(self,resource,key):
            sku,pid,number,status=('owned',10,'P-2','待下单') if key=='2' else ('second',20,'P-3','待审核')
            return dict(id=int(key),tenant_id=1,order_sn=number,warehouse_name='owned-warehouse',status_text=status,item_list=[dict(sku=sku,product_id=pid,quantity=16)])
    result=track_purchases([first,second],policy,Reader(),discover=True)
    assert result['registeredSkuCount']==2 and result['discoveryComplete']
    assert [(r['erpId'],r['skus'],r['status']) for r in result['items']]==[('2',['owned'],'待下单'),('3',['second'],'待审核')]
    assert result['failedCount']==0 and result['businessWrites']==0


def test_discovery_failure_keeps_exact_known_ids_and_marks_scope_incomplete():
    item,policy=sample()
    class Reader:
        def read(self,*args,**kwargs):raise ERPError('ERP_TIMEOUT')
        def detail(self,*args):return dict(id=2,tenant_id=1,order_sn='P-2',warehouse_name='owned-warehouse',status_text='待审核',item_list=[dict(sku='owned',quantity=8)])
    result=track_purchases([item],policy,Reader(),discover=True)
    assert result['items'][0]['verified'] and not result['discoveryComplete']
    assert result['discoveryErrors']==[dict(warehouseName='owned-warehouse',code='ERP_TIMEOUT')]


def test_discovery_excludes_other_products_and_requires_product_id_for_new_references():
    item,policy=sample();item['pendingPurchases']=[]
    class Reader:
        def read(self,*args,**kwargs):
            return SimpleNamespace(complete=True,records=[dict(id=i,tenant_id=1,order_sn=f'P-{i}',warehouse_name='owned-warehouse',
                item_list=[dict(sku=sku,product_id=pid)]) for i,sku,pid in [(3,'owned',99),(4,'other',10),(5,'owned',None)]])
        def detail(self,*args):raise AssertionError('Unverified reference must not be read')
    assert track_purchases([item],policy,Reader(),discover=True)['items']==[]


def test_discovery_rejects_unscoped_server_results_before_reading_any_ids():
    item,policy=sample();item['pendingPurchases']=[]
    class Reader:
        def read(self,*args,**kwargs):return SimpleNamespace(complete=True,records=[dict(id=3,tenant_id=99,warehouse_name='elsewhere')])
        def detail(self,*args):raise AssertionError('Unscoped ID')
    result=track_purchases([item],policy,Reader(),discover=True)
    assert result['items']==[] and not result['discoveryComplete']
    assert result['discoveryErrors'][0]['code']=='PURCHASE_TRACKING_RELATION_CHANGED'
