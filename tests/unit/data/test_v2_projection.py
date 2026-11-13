from copy import deepcopy
import pytest
from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.projection.v2 import entities
from commerce_hub.data.sync.v2_catalog import collect_catalog
from commerce_hub.scenarios.s01_v2.analysis import analyze,statistics
from commerce_hub.scenarios.s01_v2.requisition import V2RequisitionService
from tests.support.v2 import SyntheticERP,MemoryCheckpoint


def ready(tmp_path,count=5):
    erp=SyntheticERP(count);reader=erp.reader(tmp_path);catalog=collect_catalog(reader,'1')
    return erp,reader,catalog,entities(catalog,'1')


def test_1000_paginated_objects_complete_and_new_sku_discovered_without_id_registration(tmp_path):
    erp,reader,catalog,values=ready(tmp_path,1000)
    assert len(values)==1000 and all(e['identityVerified'] for e in values)
    results=[analyze(catalog,e,reader) for e in values]
    s=statistics(results)
    assert s['discoveredSkuCount']==s['scopeObjectCount']==s['erpReference']==s['processedCount']==1000
    assert s['coverage']==s['processingCoverage']==1 and s['modelCalls']==s['businessMutations']==erp.mutations==0
    assert reader.state['requestCount']<40 # Common pages, not thousands of per-SKU Agent calls.
    assert all(int(params.get('limit',1))<=100 for _,path,params in erp.calls if path=='/api/v1/supplier-quotes')
    erp.add(1000);new=erp.reader(tmp_path/'new')
    assert len(entities(collect_catalog(new,'1'),'1'))==1001


def test_zero_empty_failure_and_no_listing_are_distinct(tmp_path):
    erp,reader,catalog,values=ready(tmp_path)
    catalog['suggestions']['rows'][0]['suggested_qty']=0
    zero=analyze(catalog,values[0] if values[0]['productId']=='1' else next(e for e in values if e['productId']=='1'),reader)
    assert zero['sourceGrade']=='REFERENCE_ONLY' and zero['sourceQuantity']==0 and zero['quantity'] is None
    assert zero['analysisState']=='NEEDS_REVIEW' and not zero['procurementEligibility']['eligible']
    catalog['suggestions']['rows']=[]
    empty=analyze(catalog,values[0],reader)
    assert empty['sourceGrade']=='UNAVAILABLE' and empty['analysisState']!='NO_REPLENISHMENT'
    erp.fail_resource='replenishment'
    failed=collect_catalog(erp.reader(tmp_path/'failed'),'1')
    assert not failed['suggestions']['complete'] and failed['suggestions']['error']=='ERP_503'


def test_store_warehouse_overlap_retained_without_duplicate_suggestion_or_inventory_buckets(tmp_path):
    erp,reader,catalog,values=ready(tmp_path,1)
    inv=deepcopy(catalog['inventory']['rows'][0]);inv.update(id=999,wid=2,warehouse_name='Another Warehouse',quantity=40,available=40)
    catalog['warehouses']['rows'].append(dict(id=2,tenant_id=1,name='Another Warehouse'))
    catalog['inventory']['rows'].append(inv)
    e=entities(catalog,'1')
    assert len(e)==3 # Two actual store/warehouse stocks plus unresolved suggestion relation.
    assert sum(bool(x['suggestionIds']) for x in e)==1
    assert not next(x for x in e if x['suggestionIds'])['identityVerified']


def test_bad_inventory_sku_link_does_not_hide_the_actual_catalog_product(tmp_path):
    erp,reader,catalog,values=ready(tmp_path,1)
    catalog['inventory']['rows'][0]['sku']='ORPHAN-SKU'
    catalog['suggestions']['rows']=[]
    found=entities(catalog,'1')
    assert {e['sku'] for e in found}=={'V2-SKU-0','ORPHAN-SKU'}
    assert all(not e['identityVerified'] for e in found)


def test_reference_only_and_unknown_algorithm_do_not_block_scheme_b(tmp_path):
    erp,reader,catalog,values=ready(tmp_path,1)
    result=analyze(catalog,values[0],reader)
    assert result['sourceGrade']=='REFERENCE_ONLY' and result['procurementEligibility']['eligible']
    assert 'ERP_ALGORITHM_UNKNOWN' in result['uncertainties']
    assert V2RequisitionService.validate_quantity(dict(dataReport=dict(item=result)),120,'')=='120'
    with pytest.raises(Exception,match='MOQ_OR_CARTON'):V2RequisitionService.validate_quantity(dict(dataReport=dict(item=result)),13,'changed')


@pytest.mark.parametrize('field,value,code',[('unit',None,'PROCUREMENT_UNIT_UNCONFIRMED'),('default_carton_qty',0,'CARTON_QUANTITY'),('supplier_name',None,'SUPPLIER_RELATION')])
def test_necessary_constraints_remain_hard_blocks(tmp_path,field,value,code):
    erp,reader,catalog,values=ready(tmp_path,1);catalog['products']['rows'][0][field]=value
    if field=='supplier_name':catalog['quotes']['rows'][0]['supplier_id']=None
    result=analyze(catalog,values[0],reader)
    assert not result['procurementEligibility']['eligible']
    assert any(code in c for c in result['procurementEligibility']['hardBlocks'])


def test_unique_related_quote_can_establish_supplier_without_product_display_name(tmp_path):
    erp,reader,catalog,values=ready(tmp_path,1);catalog['products']['rows'][0]['supplier_name']=None
    result=analyze(catalog,values[0],reader)
    assert result['procurementEligibility']['eligible'] and result['constraints']['supplierId']=='5'


def test_duplicate_suggestions_are_retained_without_choosing_an_arbitrary_quantity(tmp_path):
    erp,reader,catalog,_=ready(tmp_path,1)
    other=deepcopy(catalog['suggestions']['rows'][0]);other.update(id=999,suggested_qty=240)
    catalog['suggestions']['rows'].append(other)
    item=analyze(catalog,entities(catalog,'1')[0],reader)
    assert item['sourceSuggestionCount']==2 and len(item['sourceSuggestions'])==2
    assert item['quantity'] is None and item['sourceGrade']=='UNVERIFIED'
    assert not item['procurementEligibility']['eligible']


def test_formal_purchase_is_visible_without_invented_deduction_and_other_warehouse_is_not_duplicate(tmp_path):
    erp,reader,catalog,values=ready(tmp_path,1)
    source=catalog['suggestions']['rows'][0]
    purchase=dict(id=999,order_sn='FORMAL',status_text='待到货',warehouse_name='Different Warehouse',
        source_plan_no=source['recommendation_no'],item_list=[dict(sku=values[0]['sku'],quantity=200,received_qty=20)])
    catalog['formalPurchases']['rows']=[purchase]
    item=analyze(catalog,values[0],reader)
    assert item['procurementEligibility']['eligible']
    po=item['formalPurchases'][0]
    assert po['unreceivedQuantity']==180 and po['effectiveSupplyQuantity'] is None and not po['includedInCalculation']
    assert 'RELATED_PURCHASE_TARGETS_DIFFERENT_WAREHOUSE' in item['uncertainties']
    purchase['warehouse_name']=values[0]['warehouseName']
    assert 'KNOWN_FORMAL_PURCHASE_FOR_SOURCE_PLAN' in analyze(catalog,values[0],reader)['procurementEligibility']['hardBlocks']


@pytest.mark.parametrize('change,code',[
    ('moq','MOQ_OR_CARTON_VIOLATION'),('carton','MOQ_OR_CARTON_VIOLATION'),
    ('quote','REQUISITION_SOURCE_NOT_ELIGIBLE'),('scope','REQUISITION_SOURCE_NOT_ELIGIBLE'),
    ('zero','REQUISITION_SOURCE_NOT_ELIGIBLE')])
def test_scheme_b_negative_constraints_are_enforced_on_server(tmp_path,change,code):
    erp,reader,catalog,values=ready(tmp_path,1)
    if change=='quote':catalog['quotes']['rows'][0]['status']='expired'
    if change=='scope':values[0]['identityVerified']=False
    if change=='zero':catalog['suggestions']['rows'][0]['suggested_qty']=0
    item=analyze(catalog,values[0],reader)
    qty=8 if change=='moq' else 121 if change=='carton' else 120
    with pytest.raises(Exception,match=code):V2RequisitionService.validate_quantity(dict(dataReport=dict(item=item)),qty,'manual')


def test_source_permission_change_blocks_recovery_before_cached_rows_are_reused(tmp_path):
    import json
    erp=SyntheticERP(5);cp=MemoryCheckpoint();reader=erp.reader(tmp_path,cp)
    reader.authenticate('1');reader.resource('products','/api/v1/products')
    resumed=erp.reader(tmp_path,cp);original=resumed.transport
    def changed(method,path,*args):
        if path=='/api/v1/me':return 200,json.dumps(dict(tenant_id=1,role='restricted')).encode()
        return original(method,path,*args)
    resumed.transport=changed
    with pytest.raises(ERPError,match='V2_SOURCE_AUTHORIZATION_CHANGED'):resumed.authenticate('1')


def test_budget_and_page_checkpoint_survive_new_reader(tmp_path):
    erp=SyntheticERP(1000);cp=MemoryCheckpoint()
    r=erp.reader(tmp_path,cp,request_limit=3,page_size=200)
    r.authenticate('1');batch=r.resource('products','/api/v1/products')
    assert not batch['complete'] and batch['error']=='V2_REQUEST_BUDGET_EXHAUSTED' and len(batch['rows'])==400
    before=len(erp.calls)
    resumed=erp.reader(tmp_path,cp,request_limit=3,page_size=200)
    batch=resumed.resource('products','/api/v1/products')
    assert len(batch['rows'])==400 and len(erp.calls)==before and resumed.state['requestCount']==3


def test_dynamic_new_sku_uses_original_normalizer_and_b01_b02_without_registered_ids():
    from tests.unit.data.test_owned import owned_case
    from types import SimpleNamespace
    m,captures,receipt=owned_case()
    sku='NEW-DYNAMIC-SKU'
    for cap in captures.values():
        for r in cap['rows']:
            if r.get('sku'):r['sku']=sku
            for line in r.get('item_list',[]):line['sku']=sku
    captures['product']['rows'][0].update(name='New Dynamic Product',supplier_name='Synthetic Supplier')
    captures['quotes']['rows'][0].update(supplier_name='Synthetic Supplier',currency='USD')
    captures['store']['rows'][0]['store_name']=m.storeName
    captures['warehouse']['rows'][0]['name']=m.warehouseName
    captures['inventory']['rows'][0].update(store_name=m.storeName,warehouse_name=m.warehouseName)
    catalog={name:deepcopy(captures[key]) for name,key in [('products','product'),('stores','store'),('warehouses','warehouse'),('inventory','inventory'),('quotes','quotes'),('sales','sales'),('listings','listing')]}
    catalog.update(suggestions=dict(rows=[],complete=True,total=0),formalPurchases=dict(rows=[],complete=True,total=0),businessDate='2026-11-13')
    class Reader:
        state=dict(startedAt=receipt['completedAt'])
        def resource(self,name,*args,**kwargs):
            if name.startswith('ledger-scope'):
                rows=[r for k,v in captures.items() if k.startswith('ledger-') for r in v['rows']]
                return dict(rows=deepcopy(rows),complete=True,total=len(rows))
            return deepcopy(captures['supplier' if name.startswith('supplier-') else name])
    values=entities(catalog,'1');assert len(values)==1 and values[0]['identityVerified']
    result=analyze(catalog,values[0],Reader())
    assert result['sourceGrade']=='RULE_CALCULATED' and result['quantity']==48
    assert result['ruleResult']['forecast']['totalSales']=='39'
    assert result['ruleResult']['supplyDemand']['baseline']['availableQuantity']=='6'
    assert result['constraints']['orderMultiple']==8
