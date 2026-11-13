"""Online normalization fixtures and independent arithmetic expectations, no live ERP."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import pytest
from tests.unit.data.test_online import mapping,pages
from commerce_hub.data.sync.online import TEACHING_BATCH
from commerce_hub.data.projection.online import observed,normalize_online
from commerce_hub.data.quality.online import capture_online
from commerce_hub.scenarios.s01_backend.online import OnlineS01Handler

def teaching():
    m=mapping().model_copy(update=dict(sku=TEACHING_BATCH+'-A',teachingReplay=True))
    now=datetime.now(timezone.utc).isoformat();source=pages()
    for rows in source.values():
        for row in rows:row.update(sku=m.sku,updated_at=now)
    source['products'][0]['product_type']='TEACHING_SIMULATION';source['products'][0]['moq']=12
    data={name:dict(rows=source[key],complete=True,total=len(source[key]),fingerprint='a'*64,observedAt=now)
        for name,key in [('inventory','inventory'),('product','products'),('store','store-authorizations'),
        ('warehouse','warehouses'),('listing','listings')]}
    for day,q in enumerate([8,10,9,11,12,14,13],1):
        data[f'sales-{day}']=dict(complete=True,rows=[dict(id=day,tenant_id=1,order_sn=TEACHING_BATCH+f'-SALE-202611{day:02d}',
            store_name='store',shipping_warehouse='warehouse',order_time=f'2026-11-{day:02d} 12:00:00',updated_at=now,
            item_list=[dict(sku=m.sku,quantity=q)])],fingerprint='b'*64)
    data['purchases']=dict(complete=True,rows=[],fingerprint='c'*64)
    data['purchase-draft']=dict(complete=True,rows=[dict(status_text='DRAFT')],fingerprint='d'*64)
    data['quality']=dict(complete=True,rows=[dict(order_sn=TEACHING_BATCH+'-QC-A',tenant_id=1,warehouse_name='warehouse',
        item_list=[dict(sku=m.sku)],qc_status='TEACHING_QUALITY_CLEAR')],fingerprint='e'*64)
    receipt=dict(acquisitionId='a'*32,completedAt=now,startedAt=now,mappingVersion=m.version,
        taskRef=dict(tenantId=m.scope['tenantId'],taskId='task'),planVersion='1')
    return m,data,receipt

def result(m,data,receipt):
    projection,verified=observed(data,m,receipt)
    normalized=normalize_online(data,m,receipt,verified)
    return OnlineS01Handler.rules_result(capture_online(projection,receipt,verified,normalized))

def test_online_teaching_input_consumes_existing_b01_b02_without_reserved_double_deduction():
    value=result(*teaching());supply=value.dataReport['supplyDemand']
    assert value.sourceNature=='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'
    assert supply['baseline']['availableQuantity']=='50'
    assert supply['baseline']['gapQuantity']=='27'
    assert supply['baseline']['closingBalance']=='-27'
    assert supply['candidates'][0]['quantity']=='30'
    assert supply['candidates'][0]['evaluation']['closingBalance']=='3'
    assert supply['candidates'][0]['evaluation']['stockoutRisk'] is True
    assert value.dataReport['scenarioSupplement']['procurementEligible'] is False

@pytest.mark.parametrize('fault',['missing-sale','wrong-date','foreign-sku','duplicate-order','unknown-supply','mapping','timeout'])
def test_unknown_online_facts_never_generate_a_false_candidate(fault):
    m,data,receipt=teaching()
    if fault=='missing-sale':data['sales-4']['rows']=[]
    if fault=='wrong-date':data['sales-4']['rows'][0]['order_time']='2026-01-01 12:00:00'
    if fault=='foreign-sku':data['sales-4']['rows'][0]['item_list'][0]['sku']='foreign'
    if fault=='duplicate-order':data['sales-4']['rows'][0]['id']=1
    if fault=='unknown-supply':data['purchase-draft']['rows'][0]['status_text']=None
    if fault=='mapping':data['inventory']['rows'][0]['store_id']=999
    if fault=='timeout':data['sales-4'].update(error='ERP_TIMEOUT',complete=False,rows=[])
    value=result(m,data,receipt)
    assert value.completeness=='BLOCKED'
    assert value.dataReport['supplyDemand']['baseline'] is None
    assert value.dataReport['supplyDemand']['candidates']==[]

@pytest.mark.parametrize('fault',['stale','future','quality','unknown-moq'])
def test_freshness_and_candidate_constraints_stay_in_d03(fault):
    m,data,receipt=teaching()
    if fault in {'stale','future'}:
        data['inventory']['rows'][0]['updated_at']=(datetime.now(timezone.utc)+timedelta(hours=-25 if fault=='stale' else 1)).isoformat()
    if fault=='quality':data['quality']['rows'][0]['qc_status']='TEACHING_QUALITY_INVESTIGATE'
    if fault=='unknown-moq':data['product']['rows'][0]['moq']=None
    value=result(m,data,receipt)
    assert value.dataReport['supplyDemand']['candidates']==[]
    assert (value.dataReport['supplyDemand']['baseline'] is None)==(fault in {'stale','future'})

def test_box_quantity_never_changes_the_independent_teaching_multiple():
    m,data,receipt=teaching();data['product']['rows'][0]['default_carton_qty']=999
    value=result(m,data,receipt)
    assert value.dataReport['supplyDemand']['candidates'][0]['quantity']=='30'
