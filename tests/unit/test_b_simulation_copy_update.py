"""No ERP network. Exercise durable reconciliation and unchanged-field checks."""
from copy import deepcopy
import json
import pytest
from tools.b_simulation_copy_update import execute
from tools.s01_teaching_dataset import DatasetError


PLAN=[dict(resource='products',id='362',key='sku',value='owned-sku',fields=dict(name='自然商品名'))]


class Client:
    def __init__(self):self.item=dict(id=362,tenant_id=1,sku='owned-sku',name='旧名称',stock=3);self.writes=0;self.lose=False;self.corrupt=False
    def request(self,method,path,values=None):
        if path.endswith('/data-contract'):return dict(kind='synthetic')
        if path.endswith('/me'):return dict(tenant_id=1)
        if method=='PUT':
            self.writes+=1;self.item.update(values)
            if self.corrupt:self.item['stock']=4
            if self.lose:raise TimeoutError('test-only lost receipt')
        return deepcopy(self.item)


def test_uncertain_response_is_read_back_by_original_id_and_not_resent(tmp_path):
    client=Client();client.lose=True
    with pytest.raises(TimeoutError):execute(client,PLAN,tmp_path)
    client.lose=False
    assert execute(client,PLAN,tmp_path)['verified']==1 and client.writes==1


def test_uncertain_unapplied_write_cannot_be_blindly_retried(tmp_path):
    client=Client();client.lose=True
    with pytest.raises(TimeoutError):execute(client,PLAN,tmp_path)
    client.item['name']='旧名称';client.lose=False
    with pytest.raises(DatasetError,match='COPY_UNKNOWN_REQUIRES_RECONCILIATION'):execute(client,PLAN,tmp_path)
    assert client.writes==1


def test_foreign_record_and_inventory_change_are_rejected(tmp_path):
    client=Client();client.item['tenant_id']=2
    with pytest.raises(DatasetError,match='COPY_OWNERSHIP_MISMATCH'):execute(client,PLAN,tmp_path)
    assert client.writes==0
    client.item['tenant_id']=1;client.corrupt=True
    with pytest.raises(DatasetError,match='COPY_UNRELATED_FIELD_CHANGED'):execute(client,PLAN,tmp_path)
