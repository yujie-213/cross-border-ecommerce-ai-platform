import json
import pytest
from commerce_hub.adapters.erp import ERPConfig, ERPError, TeachingERPReader
from commerce_hub.adapters.erp_requisition import TeachingRequisitionClient


def payload():
    return dict(order_sn='fixture-rq',supplier_id=1,supplier_name='Synthetic',warehouse_name='Synthetic',
        order_time='2026-11-13 12:00:00',purchase_currency='USD',amount=115.2,purchase_user='fixture',
        source_plan_no='fixture-operation',remark='fixture',
        item_list=[dict(sku='fixture',product_id=1,quantity=48,unit_price=2.4,amount=115.2)])


def test_narrow_mutations_have_exact_paths_and_bodies_no_workflow_bypass():
    calls = []
    def transport(method,path,headers,body,config):
        calls.append((method,path,json.loads(body)))
        return (201 if path.endswith('purchase-orders') else 200), b'{"code":0}'
    client = TeachingRequisitionClient(ERPConfig(access_token='fixture-only'),transport=transport,sleeper=lambda _:None)
    client.create_requisition(payload());client.submit_requisition('91')
    assert calls == [('POST','/api/v1/purchase-orders',payload()),('POST','/api/v1/workflows/purchase-orders/91/submit',{})]
    assert all(not any(word in e['path'] for word in ('decide','place-order','receive','confirm')) for e in client.events)


@pytest.mark.parametrize('fault',['status','received','pending','line-received'])
def test_forbidden_managed_fields_rejected_before_network(fault):
    p = payload()
    if fault == 'line-received':p['item_list'][0]['received_qty'] = 48
    else:p[{'status':'status_text','received':'received_qty','pending':'pending_qty'}[fault]] = 48
    client = TeachingRequisitionClient(ERPConfig(access_token='fixture-only'),transport=lambda *_:pytest.fail('No IO'),sleeper=lambda _:None)
    with pytest.raises(ERPError,match='PAYLOAD_REJECTED'):client.create_requisition(p)


def test_unknown_send_has_no_transport_retry_and_d01_cannot_write():
    calls = []
    def timeout(*_):calls.append(1);raise TimeoutError()
    client = TeachingRequisitionClient(ERPConfig(access_token='fixture-only'),transport=timeout,sleeper=lambda _:None)
    with pytest.raises(ERPError,match='ERP_SEND_UNKNOWN'):client.create_requisition(payload())
    assert len(calls) == 1
    reader = TeachingERPReader(ERPConfig(access_token='fixture-only'),transport=lambda *_:pytest.fail('No IO'))
    with pytest.raises(ERPError,match='ALLOWLISTED'):reader.read('/api/v1/purchase-orders',payload(),method='POST')
