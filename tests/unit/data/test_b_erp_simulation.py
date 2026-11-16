"""Import safety checks. Synthetic clients here are not ERP business evidence."""
from copy import deepcopy
from datetime import date
import pytest

from tools.b_erp_simulation_dataset import Client, Importer, DatasetError, plan, profiles


class MemoryClient:
    def __init__(self):
        self.rows=[];self.writes=[];self.lost_response=False

    def exact(self,resource,key,value):
        return deepcopy(self.rows)

    def request(self,method,path,payload):
        self.writes.append((method,path,payload))
        self.rows=[dict(payload,id=10001,tenant_id=1)]
        if self.lost_response:raise DatasetError('ERP_TIMEOUT')
        return self.rows[0]


def test_fixed_counts_and_complete_business_days():
    p=plan();items=profiles()
    assert p['newSkus']==len(items)==3
    assert sum(len(x['quantities']) for x in items)==p['salesOrders']==30
    assert sum(len(x['tickets']) for x in items)==p['customerTickets']==12
    assert len(set(p['saleBusinessDates']))==7
    assert max(date.fromisoformat(d) for d in p['saleBusinessDates'])<date(2026,11,16)
    assert all(x['closing']>0 for x in items)
    assert p['noExternalTransactions'] and p['noModelCalls'] and p['noHumanRiskDecisions']


def test_create_independent_read_and_resume_without_duplicate(tmp_path):
    c=MemoryClient();i=Importer(tmp_path,c)
    payload=dict(sku='SIM-TEST',name='fictional')
    a=i.create('products','sku','SIM-TEST',payload)
    b=Importer(tmp_path,c).create('products','sku','SIM-TEST',payload)
    assert a==b and len(c.writes)==1


def test_foreign_existing_record_never_adopted(tmp_path):
    c=MemoryClient();c.rows=[dict(sku='SIM-TEST',id=1,tenant_id=1)]
    with pytest.raises(DatasetError,match='EXISTING_RECORD_NOT_OWNED'):
        Importer(tmp_path,c).create('products','sku','SIM-TEST',dict(sku='SIM-TEST'))
    assert not c.writes


def test_unknown_response_recovered_by_original_key_read_only(tmp_path):
    c=MemoryClient();c.lost_response=True;i=Importer(tmp_path,c)
    with pytest.raises(DatasetError,match='ERP_TIMEOUT'):
        i.create('products','sku','SIM-TEST',dict(sku='SIM-TEST'))
    c.lost_response=False
    assert Importer(tmp_path,c).create('products','sku','SIM-TEST',dict(sku='SIM-TEST'))['id']==10001
    assert len(c.writes)==1


def test_unknown_absent_record_not_resent(tmp_path):
    c=MemoryClient();i=Importer(tmp_path,c);c.lost_response=True
    with pytest.raises(DatasetError):i.create('products','sku','SIM-TEST',dict(sku='SIM-TEST'))
    c.rows=[];c.lost_response=False
    with pytest.raises(DatasetError,match='UNKNOWN_WRITE_NOT_FOUND_NO_RESEND'):
        Importer(tmp_path,c).create('products','sku','SIM-TEST',dict(sku='SIM-TEST'))
    assert len(c.writes)==1


def test_changed_payload_rejected_before_retry(tmp_path):
    c=MemoryClient();i=Importer(tmp_path,c)
    i.create('products','sku','SIM-TEST',dict(sku='SIM-TEST'))
    with pytest.raises(DatasetError,match='PAYLOAD_CHANGED'):
        Importer(tmp_path,c).create('products','sku','SIM-TEST',dict(sku='SIM-TEST',name='changed'))
    assert len(c.writes)==1


@pytest.mark.parametrize('path',[
    '/api/v1/purchase-orders','/api/v1/sales-returns/1/authorize',
    '/api/v1/sales-returns/1/receive','/api/v1/sales-returns/1/refund',
    '/api/v1/customer-voice','/api/v1/sales-workflow/999/ship'])
def test_dangerous_and_unowned_routes_denied(path):
    client=object.__new__(Client);client.owned_sales=set();client.owned_listing_paths=set()
    with pytest.raises(DatasetError,match='OPERATION_DENIED'):
        client._allow('POST',path,auth=False)
