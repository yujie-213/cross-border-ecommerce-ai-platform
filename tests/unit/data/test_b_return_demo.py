"""Safety of the explicitly authorized local teaching importer, no ERP IO."""
from copy import deepcopy
import pytest
from tools.b_return_demo_dataset import DemoClient,DemoImporter,DatasetError,plan


@pytest.mark.parametrize('path',[
    '/api/v1/store-authorizations','/api/v1/warehouses','/api/v1/suppliers',
    '/api/v1/purchase-orders','/api/v1/customer-voice',
    '/api/v1/sales-returns/91/refund','/api/v1/sales-returns/92/receive',
])
def test_demo_cannot_create_store_warehouse_or_supplier_refund_or_write_other_return(path):
    c=object.__new__(DemoClient);c.owned_returns={'91'};c.owned_sales=set();c.owned_listing_paths=set()
    with pytest.raises(DatasetError):c._allow('POST',path,auth=False)


class LostReturnResponse:
    def __init__(self):
        self.owned_returns=set();self.posts=0
        self.record=dict(id=91,order_id=81,local_only=True,state='draft',authorized_at=None)
    def request(self,method,path,payload=None):
        if method=='POST':
            self.posts+=1;self.record.update(state='authorized',authorized_at='2026-11-17T00:00:00Z')
            raise DatasetError('ERP_TIMEOUT')
        return deepcopy(self.record)


def test_return_unknown_send_is_recovered_from_exact_readback_without_resend(tmp_path):
    c=LostReturnResponse();draft=dict(id=91,order_id=81)
    with pytest.raises(DatasetError):DemoImporter(tmp_path,c).return_action(draft,'authorize')
    result=DemoImporter(tmp_path,c).return_action(draft,'authorize')
    assert result['state']=='authorized' and c.posts==1
    assert plan()['newStores']==plan()['newWarehouses']==plan()['newSuppliers']==0
