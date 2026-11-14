"""Synthetic exact-resource membership and product counterexamples; zero live calls."""
from copy import deepcopy
import pytest
from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.sync.registered_catalog import collect_registered,registered_entities
from commerce_hub.data.projection.v2 import entities
from commerce_hub.scenarios.s01_v2.analysis import analyze,statistics
from tests.support.admission_runtime import AdmissionERP


def setup(tmp_path):
    erp=AdmissionERP();r=erp.reader(tmp_path);r.state['startedAt']='2026-11-14T06:00:00+00:00'
    return erp,r,erp.mapping


def test_registered_full_history_without_shared_scan_and_next_day_does_not_invalidate(tmp_path):
    erp,r,m=setup(tmp_path);c=collect_registered(r,'1',[m]);e=registered_entities(c,entities(c,'1'))[0];item=analyze(c,e,r)
    assert item['decision']['forecast']['totalSales']=='39' and item['decision']['referenceReplenishmentQuantity']==45
    assert item['quantity']==48 and c['sales']['complete'] and c['sales']['total']==7
    assert all('ids' in params and 'date_from' not in params for _,path,params in erp.calls if path=='/api/v1/sales-orders')
    r2=erp.reader(tmp_path/'tomorrow');r2.state['startedAt']='2026-11-15T06:00:00+00:00'
    c2=collect_registered(r2,'1',[m]);e2=registered_entities(c2,entities(c2,'1'))[0]
    assert analyze(c2,e2,r2)['decision']['referenceReplenishmentQuantity']==45
    assert erp.mutations==0 and r.state['requestCount']<20


def test_empty_registry_never_falls_back_to_whole_tenant(tmp_path):
    erp,r,m=setup(tmp_path);c=collect_registered(r,'1',[])
    assert registered_entities(c,entities(c,'1'))==[] and not c['sales']['rows']
    assert [path for _,path,_ in erp.calls]==['/api/v1/me']


def test_removed_inventory_preserves_demand_but_never_invents_gap(tmp_path):
    erp,r,m=setup(tmp_path);erp.data['inventory']=[]
    c=collect_registered(r,'1',[m]);rows=registered_entities(c,entities(c,'1'));assert len(rows)==1
    item=analyze(c,rows[0],r)
    assert not c['inventory']['complete'] and item['decision']['forecast']['available']
    assert item['decision']['referenceReplenishmentQuantity'] is None and item['quantity'] is None


def test_membership_change_blocks_checkpoint_reuse_before_network(tmp_path):
    erp,r,m=setup(tmp_path);collect_registered(r,'1',[m]);before=len(erp.calls)
    with pytest.raises(ERPError,match='V2_REGISTERED_SCOPE_CHANGED'):collect_registered(r,'1',[])
    assert len(erp.calls)==before


def test_shared_prefix_and_other_warehouses_never_confer_membership(tmp_path):
    erp,r,m=setup(tmp_path)
    extra=deepcopy(erp.data['inventory'][0]);extra.update(id=999,wid=9,warehouse_name='Unregistered Warehouse')
    erp.data['inventory'].append(extra);erp.data['warehouses'].append(dict(id=9,tenant_id=1,name='Unregistered Warehouse'))
    c=collect_registered(r,'1',[m]);rows=registered_entities(c,entities(c,'1'))
    assert len(rows)==1 and rows[0]['warehouseId']=='3' and c['inventory']['total']==1
    # A stale caller cannot use the owned single route to request the other warehouse.
    rogue=dict(rows[0],warehouseId='9')
    with pytest.raises(ERPError,match='V2_BUSINESS_SCOPE_NOT_REGISTERED'):collect_registered(erp.reader(tmp_path/'rogue'),'1',[m],rogue)


def test_two_registered_warehouses_independent_sales_stock_and_sku_statistics(tmp_path):
    erp,r,m=setup(tmp_path);b=m.monitor.model_copy(update=dict(inventoryIds=('99',),salesIds=('199',),listingId='299'))
    second=m.model_copy(update=dict(sourceWarehouse='9',warehouseName='Second Fixture Warehouse',monitor=b))
    erp.data['warehouses'].append(dict(id=9,tenant_id=1,name=second.warehouseName))
    stock=deepcopy(erp.data['inventory'][0]);stock.update(id=99,wid=9,warehouse_name=second.warehouseName,quantity=500,available=500);erp.data['inventory'].append(stock)
    sale=deepcopy(erp.data['sales'][0]);sale.update(id=199,shipping_warehouse=second.warehouseName);sale['item_list'][0]['quantity']=2;erp.data['sales'].append(sale)
    erp.data['listings'].append(dict(id=299,tenant_id=1,sku=m.sku,store_name=m.storeName))
    c=collect_registered(r,'1',[m,second]);rows=[analyze(c,e,r) for e in registered_entities(c,entities(c,'1'))]
    assert [i['decision']['referenceReplenishmentQuantity'] for i in rows]==[45,0]
    assert [i['decision']['forecast']['totalSales'] for i in rows]==['39','2']
    s=statistics(rows,'product-counts-v1');assert s['discoveredSkuCount']==1 and s['judgedScopeCount']==2 and s['replenishScopeCount']==1


def test_source_does_not_honor_id_scope_is_rejected(tmp_path):
    erp,r,m=setup(tmp_path);original=erp.transport
    def ignored(method,target,headers,body,config):
        if '/inventory?' in target:
            import json
            rogue=dict(erp.data['inventory'][0],id=999)
            return 200,json.dumps(dict(items=[rogue],total=1)).encode()
        return original(method,target,headers,body,config)
    r.transport=ignored
    with pytest.raises(ERPError,match='V2_REGISTERED_RESOURCE_MISMATCH'):collect_registered(r,'1',[m])
