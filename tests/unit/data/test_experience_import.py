"""Offline import reconciliation counterexamples, never a live ERP test."""
from copy import deepcopy
import pytest
from tools.s01_experience_finalize import reconcile_inventory,PROFILES
from tools.s01_experience_dataset import DatasetError,Client


def member():
    return dict(initial=20,inventory=dict(id=99),product=dict(sku='fixture'),warehouse=dict(name='fixture warehouse'),
        expectedAvailable=17,expectedOutboundQuantities={'7':3},finalInventory=dict(quantity=17,available=17))


def movements():
    return [dict(id=1,inventory_id=99,sku='fixture',warehouse_name='fixture warehouse',resource='outbound-orders',record_id=7,
        operation='post',reverses_id=None,before_quantity=20,before_available=20,delta_quantity=-3,delta_available=-3,after_quantity=17,after_available=17)]


def test_realistic_profiles_have_normal_names_models_brand_inputs_and_pricing():
    assert len(PROFILES)==8
    for p in PROFILES.values():
        assert p['name'] and p['model'] and p['category'] and p['material'] and p['spec']
        assert p['price']>p['cost']>0
        assert not any(w in p['name'] for w in ['缺货','下降','待核实','新品','采购条件'])


def test_closed_balance_requires_unique_sale_outbound_relation():
    assert reconcile_inventory(member(),movements())['closing']==17
    with pytest.raises(DatasetError,match='DUPLICATE_LEDGER_EVENT'):reconcile_inventory(member(),movements()*2)


@pytest.mark.parametrize('field,value',[('before_quantity',19),('after_available',18),('inventory_id',100),('sku','other'),('record_id',8)])
def test_same_final_number_does_not_mask_broken_business_links(field,value):
    rows=deepcopy(movements());rows[0][field]=value
    with pytest.raises(DatasetError):reconcile_inventory(member(),rows)


@pytest.mark.parametrize('path',['/api/v1/purchase-orders','/api/v1/workflows/purchase-orders/7/submit','/api/v1/inbound-orders','/api/v1/sales-workflow/7/ship'])
def test_importer_does_not_authorize_purchase_receiving_or_unowned_shipments(path):
    client=object.__new__(Client)
    with pytest.raises(DatasetError):client._allow('POST',path,auth=False)
