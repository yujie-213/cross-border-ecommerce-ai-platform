from copy import deepcopy
from types import SimpleNamespace
import pytest
from commerce_hub.data.sync.owned import collect_owned
from commerce_hub.data.projection.purchases import project_purchases, FORMAL_STATES, POLICY
from tests.support.p3_requisition import FixtureERP
from tests.unit.data.test_owned import calculate


def test_new_collection_filters_at_source_never_queries_old_pending_or_draft():
    erp = FixtureERP()
    context = SimpleNamespace(check=lambda: None)
    captures, receipt = collect_owned(erp, erp.mapping, context, 'fixture-acquisition', formal_purchases=True)
    requests = [event for event in erp.calls if event[1] == '/api/v1/purchase-orders']
    assert len(requests) == len(FORMAL_STATES)
    assert {r[2]['q'] for r in requests} == set(FORMAL_STATES)
    assert all(r[2]['field'] == 'status_text' and r[2]['match'] == 'exact' and 'ids' not in r[2] for r in requests)
    assert captures['purchases']['rows'] == [] and receipt['purchasePolicy'] == POLICY
    assert 'REGISTERED_IDS_ONLY' not in receipt['limitations']


def purchase_case():
    erp = FixtureERP();m = erp.mapping
    po = dict(id=91,tenant_id=1,warehouse_name=m.warehouseName,order_sn='fixture-approved',status_text='待到货',
        item_list=[dict(sku=m.sku, quantity=48, received_qty=16),dict(sku='other-fixture',quantity=12)],
        received_qty=999,pending_qty=999,planned_arrival='2026-11-15')
    proof = dict(erpId='91', erpNumber='fixture-approved',scope=m.scope,datasetId=m.monitor.datasetId,purpose='SALES_REPLENISHMENT')
    return m, po, proof


def test_multisku_receipt_is_line_specific_never_header_or_sellable_supply():
    m,p,proof = purchase_case()
    view = project_purchases([p],m,[proof]);line = view['items'][0]
    assert len(view['items']) == 1 and line['orderedQuantity'] == '48' and line['receivedQuantity'] == '16'
    assert line['unreceivedQuantity'] == '32' and line['effectiveSupplyQuantity'] is None
    assert line['sellableDate'] is None and not line['includedInCalculation']
    del p['item_list'][0]['received_qty']
    assert project_purchases([p],m,[proof])['items'][0]['unreceivedQuantity'] is None


@pytest.mark.parametrize('fault',['store','purpose','dataset','id','number'])
def test_unknown_scope_not_promoted_by_warehouse_supplier_or_prefix(fault):
    m,p,proof = purchase_case()
    if fault == 'store': proof['scope'] = dict(m.scope,storeIds=['other'])
    elif fault == 'purpose': proof['purpose'] = 'OFFICE'
    elif fault == 'dataset': proof['datasetId'] = 'other'
    elif fault == 'id': proof['erpId'] = '999'
    else: proof['erpNumber'] = 'other'
    result = project_purchases([p],m,[proof])
    assert not result['items'] and result['unresolvedScopeCount'] == 1


@pytest.mark.parametrize('fault',['state','tenant','warehouse','duplicate','lines'])
def test_source_filter_failure_or_ambiguous_lines_fails_closed(fault):
    m,p,proof = purchase_case()
    rows = [p]
    if fault == 'state': p['status_text'] = '待审核'
    elif fault == 'tenant': p['tenant_id'] = 999
    elif fault == 'warehouse': p['warehouse_name'] = 'other'
    elif fault == 'duplicate': rows.append(deepcopy(p))
    else: p['item_list'] = []
    with pytest.raises(ValueError): project_purchases(rows,m,[proof])
