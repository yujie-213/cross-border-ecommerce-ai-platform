from types import SimpleNamespace
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


def test_tracking_failure_does_not_claim_old_status_is_current_or_drop_record():
    item,policy=sample()
    class Reader:
        def detail(self,*args):raise ERPError('ERP_AUTH_REJECTED')
    result=track_purchases([item],policy,Reader())
    assert result['failedCount']==1
    assert result['items'][0]['status'] is None and result['items'][0]['previousStatus']=='待审核'


def test_tracking_refuses_changed_ownership_and_excludes_unregistered_members():
    item,policy=sample()
    class Reader:
        def detail(self,*args):return dict(id=2,tenant_id=99)
    result=track_purchases([item],policy,Reader())
    assert result['items'][0]['error']=='PURCHASE_TRACKING_RELATION_CHANGED'
    policy.opening_binding=lambda _:None
    assert track_purchases([item],policy,Reader())['items']==[]
