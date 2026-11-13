"""Synthetic independent contracts; no copied ERP business records or network."""
from copy import deepcopy
from datetime import datetime, timedelta
import pytest
from commerce_hub.data.sync.online import OnlineMapping
from commerce_hub.data.projection.online import observed, normalize_online
from commerce_hub.data.quality.online import capture_online
from commerce_hub.scenarios.s01_backend.online import OnlineS01Handler
from commerce_hub.data.contracts import fingerprint
from commerce_hub.scenarios.s01.natural_explanation import bundle_for_result
from commerce_hub.data.contracts import AdmittedInput
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture


def owned_case(quantities=(4,5,4,6,9,5,6), opening=45):
    m = OnlineMapping(scope=dict(tenantId='owned-fixture',canonicalSkuIds=['fixture-sku'],
        storeIds=['fixture-store'],warehouseIds=['fixture-wh'],fields=['quantity']),sku='fixture-sku',
        sourceTenant='1',sourceStore='2',sourceWarehouse='3',storeName='Fixture Store',warehouseName='Fixture Warehouse',
        monitor=dict(datasetId='fixture-dataset',scopeVersion=1,importBatchId='fixture-import',productId='1',listingId='4',
            supplierId='5',quoteId='6',quoteNo='fixture-quote',inventoryIds=['7'],salesIds=[str(10+i) for i in range(7)],
            purchaseIds=['8'],openingQuantity=str(opening),evidenceDigest='a'*64))
    receipt=dict(version='s01-online-acquisition-v1',acquisitionId='fixture-acquisition',
        startedAt='2026-11-13T06:00:00+00:00',completedAt='2026-11-13T06:00:05+00:00',
        mappingVersion=m.version,monitoring=dict(datasetId=m.monitor.datasetId,scopeVersion=1),
        taskRef=dict(tenantId='owned-fixture',taskId='fixture-task'),planVersion='1')
    inv=dict(id=7,tenant_id=1,sku=m.sku,store_id=2,wid=3,product_id=1,
        quantity=opening-sum(quantities),available=opening-sum(quantities),updated_at=receipt['completedAt'])
    values=dict(product=[dict(id=1,tenant_id=1,sku=m.sku)],store=[dict(id=2,tenant_id=1)],
        warehouse=[dict(id=3,tenant_id=1)],listing=[dict(id=4,tenant_id=1,sku=m.sku,store_name=m.storeName)],
        inventory=[inv],supplier=[dict(id=5,tenant_id=1)],
        quotes=[dict(id=6,quote_no='fixture-quote',product_id=1,supplier_id=5,sku=m.sku,enabled=True,status='effective',
            valid_from='2026-11-01',valid_to='2026-12-01',minimum_quantity=12,lead_days=2,unit_price='2.40',minimum_amount='28.80',version=1)],
        purchases=[dict(id=8,tenant_id=1,warehouse_name=m.warehouseName,supplier_id=5,item_list=[dict(sku=m.sku,quantity=36)],
            status_text='待审核',pending_qty=36)],sales=[])
    balance=opening
    for i,q in enumerate(quantities):
        sid=10+i;outbound=100+i
        day=(datetime(2026,11,6)+timedelta(days=i)).strftime('%Y-%m-%d')
        posted=f'2026-11-13T05:00:{i:02d}+00:00'
        values['sales'].append(dict(id=sid,tenant_id=1,store_name=m.storeName,shipping_warehouse=m.warehouseName,
            payment_status='已支付',fulfillment_status='已发货',refund_status='无退款',
            order_time=day+' 12:00:00',created_at=posted,item_list=[dict(sku=m.sku,quantity=q)]))
        values['workflow-'+str(sid)]=[dict(code=0,data=dict(order_id=sid,local_only=True,state='shipped',shipped_at=posted,
            shipments=[dict(order_id=sid,outbound_id=outbound)]))]
        values['ledger-'+str(outbound)]=[dict(id=200+i,resource='outbound-orders',record_id=outbound,warehouse_name=m.warehouseName,
            inventory_id=7,sku=m.sku,delta_quantity=-q,delta_available=-q,before_quantity=balance,after_quantity=balance-q,
            before_available=balance,after_available=balance-q,created_at=posted,operation='post',reverses_id=None)]
        balance-=q
    captures={k:dict(rows=v,complete=True,total=len(v),fingerprint=fingerprint(v)) for k,v in values.items()}
    return m,captures,receipt


def calculate(case):
    m,c,r=case;p,valid=observed(c,m,r);n=normalize_online(c,m,r,valid)
    return n, OnlineS01Handler.rules_result(capture_online(p,r,valid,n))


def test_owned_sma_reuses_calculation_and_excludes_pending_supply():
    n,result=calculate(owned_case());s=result.dataReport['supplyDemand'];f=n['forecast']
    assert result.completeness=='RULES_ONLY' and f['totalSales']=='39'
    assert f['windowStart']=='2026-11-06' and f['windowEnd']=='2026-11-12'
    assert f['calculationHorizonDays']==9 and f['forecastQuantity']=='39.00000000000000000000000000'
    assert s['baseline']['availableQuantity']=='6' and s['baseline']['inTransitQuantity']=='0'
    assert s['candidates'][0]['quantity']=='45' and s['candidates'][0]['procurementEligible'] is False
    assert f['excludedSupply'][0]['pendingQuantity']=='36'
    assert f['constraints']['orderMultiple'] is None and n['input']['policy']['orderMultiple']=='1'
    assert all(i['severity']!='BLOCK' for i in result.dataReport['quality'])
    binding=dict(taskRef=dict(tenantId='owned-fixture',taskId='fixture-task'),planVersion='1',snapshotId=result.snapshotRef,participantId='s01')
    bundle=bundle_for_result(result,binding)
    assert {f.ref for f in bundle.context.facts} >= {'forecast','constraints','quality'}
    assert next(f for f in bundle.context.facts if f.ref=='quality').qualityGate=='BLOCKED'


def test_sufficient_inventory_does_not_make_zero_candidate():
    _,result=calculate(owned_case(opening=120));s=result.dataReport['supplyDemand']
    assert s['baseline']['gapQuantity']=='0' and s['candidates']==[]
    assert s['limitations']==['NO_REPLENISHMENT_NEEDED']


def test_complete_empty_day_is_zero_but_missing_page_blocks():
    case=owned_case();case[1]['sales']['rows'][0]['order_time']='2026-11-05 12:00:00'
    n,result=calculate(case)
    assert n['forecast']['dailySales'][0]['quantity']=='0' and result.completeness=='RULES_ONLY'
    case[1]['sales']['complete']=False
    n,result=calculate(case)
    assert n['input'] is None and result.completeness=='BLOCKED'


@pytest.mark.parametrize('fault',['foreign','unpaid','duplicate-ledger','quote-expired','unknown-po','stock-drift','wrong-parent'])
def test_owned_inputs_fail_closed(fault):
    case=owned_case();c=case[1]
    if fault=='foreign':c['sales']['rows'][0]['tenant_id']=999
    elif fault=='unpaid':c['sales']['rows'][0]['payment_status']='未支付'
    elif fault=='duplicate-ledger':c['ledger-101']['rows'][0]['id']=200
    elif fault=='quote-expired':c['quotes']['rows'][0]['status']='expired'
    elif fault=='unknown-po':c['purchases']['rows'][0]['status_text']='待下单'
    elif fault=='stock-drift':c['inventory']['rows'][0]['available']+=1
    else:c['inventory']['rows'][0]['product_id']=999
    n,result=calculate(case)
    assert n['input'] is None and result.dataReport['supplyDemand']['baseline'] is None
    assert result.dataReport['supplyDemand']['candidates']==[]


def test_stockout_history_cannot_be_treated_as_complete_uncensored_demand():
    n,result=calculate(owned_case(quantities=(4,5,4,6,9,5,12)))
    assert n['issues'][0]['code']=='HISTORICAL_STOCKOUT_DEMAND_CENSORED'
    assert result.completeness=='BLOCKED'


def test_business_timezone_excludes_partial_current_day():
    m,c,r=owned_case();r['completedAt']='2026-11-12T17:00:00+00:00'
    n,result=calculate((m,c,r))
    assert n['forecast']['windowEnd']=='2026-11-12'
    assert result.dataReport['supplyDemand']['baseline']['series'][0]['day']=='2026-11-14'
    c['sales']['rows'][-1]['order_time']='2026-11-13 00:30:00'
    assert calculate((m,c,r))[0]['input'] is None


@pytest.mark.parametrize('nature,disposition,allowed',[
    ('SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP','UNKNOWN',True),
    ('SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP','INVESTIGATE',False),
    ('TEACHING_ERP_OBSERVED','UNKNOWN',False),
])
def test_advisory_policy_never_clears_investigation_or_observed_business_quality(nature,disposition,allowed):
    n,_=calculate(owned_case());value=deepcopy(n['input']);value['sourceNature']=nature
    value['policy']['qualityDisposition']=disposition
    snapshot=capture(project(AdmittedInput.model_validate(value),'fixture-quality'))
    assert snapshot.candidates_allowed is allowed
