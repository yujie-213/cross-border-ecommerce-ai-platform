from copy import deepcopy
from datetime import date,datetime,timedelta,timezone
from types import SimpleNamespace
import pytest
from commerce_hub.data.projection.stock_basis import verify_stock
from commerce_hub.data.projection.monitor import StockCheckpoint,MonitorBinding
from commerce_hub.data.projection.runtime import evaluate_runtime,business_date
from commerce_hub.data.quality.runtime import public_admission
from tests.support.admission_runtime import runtime_case,evaluate


def test_original_seven_day_sma_and_quantity_unchanged():
    r=evaluate(runtime_case());s=r['ruleResult']['supplyDemand']
    assert r['demandWindow']['totalSales']=='39' and r['demandWindow']['validDays']==7
    assert s['baseline']['availableQuantity']=='6' and s['candidates'][0]['quantity']=='48'
    assert r['inventoryBasis']['residual']=='0' and r['inventoryBasis']['eventCount']==7
    assert r['inventoryBasis']['checkpoint']['originAt']=='2026-11-13T05:00:00+00:00'
    assert r['inventoryBasis']['checkpoint']['observedAt']=='2026-11-13T06:00:05+00:00'


def test_old_order_leaves_window_not_conservation_and_zero_day_is_not_invented():
    case=runtime_case(day='2026-11-14');r=evaluate(case)
    assert r['inventoryBasis']['status']=='VERIFIED' and r['inventoryBasis']['expectedPhysical']=='6'
    assert r['demandWindow']['totalSales']=='35' and r['demandWindow']['missingDays']==1
    assert r['ruleFailureCodes']==['DEMAND_DAY_COVERAGE_INCOMPLETE'] and r['ruleResult'] is None


def test_three_certified_zero_days_count_in_calendar_denominator():
    case=runtime_case()
    for i,s in enumerate(case['sales']):
        case['movements']['rows'][i]['created_at']=f'2026-11-06T05:00:{i:02d}+00:00'
        if i>=4:s['order_time']='2026-11-05 12:00:00'
    r=evaluate(case);w=r['demandWindow']
    assert w['complete'] and w['zeroDays']==3 and w['validDays']==7 and w['totalSales']=='19'
    assert r['ruleResult'] is not None


@pytest.mark.parametrize('fault',['scope','movements','identity','stock','duplicate','missing','foreign','arithmetic','reversal','future'])
def test_critical_evidence_is_not_relaxed(fault):
    c=runtime_case()
    if fault=='scope':c['scope_complete']=False
    if fault=='movements':c['movements']['complete']=False
    if fault=='identity':c['entity']['identityVerified']=False
    if fault=='stock':c['inventory']['rows'][0].update(quantity=8,available=8)
    if fault=='duplicate':c['movements']['rows'].append(deepcopy(c['movements']['rows'][0]))
    if fault=='missing':c['movements']['rows'].pop(2)
    if fault=='foreign':c['movements']['rows'][0]['inventory_id']=999
    if fault=='arithmetic':c['movements']['rows'][0]['after_quantity']+=1
    if fault=='reversal':c['movements']['rows'][0]['reverses_id']=999
    if fault=='future':c['movements']['rows'][0]['created_at']='2026-11-14T05:00:00+00:00'
    r=evaluate(c)
    assert r['ruleResult'] is None and r['ruleFailureCodes']
    assert 'STOCK_SALES_RECONCILIATION_FAILED' not in r['ruleFailureCodes']


@pytest.mark.parametrize('status,value',[('payment_status','未支付'),('fulfillment_status','未发货'),('status_text','已取消'),('refund_status','已退款')])
def test_nonrealized_or_refunded_order_is_classified_without_erasing_other_facts(status,value):
    c=runtime_case();extra=deepcopy(c['sales'][0]);extra.update(id=999,order_time='2026-11-10 12:00:00');extra[status]=value;c['sales'].append(extra)
    r=evaluate(c)
    assert r['inventoryBasis']['status']=='VERIFIED' and r['demandWindow']['history']
    if status=='refund_status':assert r['demandWindow']['missingDays']==1
    else:assert r['ruleResult'] is not None and r['demandWindow']['totalSales']=='39'


@pytest.mark.parametrize('block',['EFFECTIVE_QUOTE_MISSING_OR_AMBIGUOUS','QUOTE_MOQ_INVALID','CARTON_QUANTITY_MISSING_OR_INVALID','FORMAL_PURCHASE_QUERY_INCOMPLETE'])
def test_procurement_conditions_preserve_original_b01_risk(block):
    c=runtime_case();c['constraints']['hardBlocks']=[block];c['constraints']['moq']=None
    r=evaluate(c);rules=r['ruleResult']
    assert rules['supplyDemand']['baseline']['stockoutRisk'] and rules['supplyDemand']['candidates']==[]
    assert r['riskOnly'] and r['dataQuality']['demand']['status']=='VERIFIED'


def test_no_replenishment_never_creates_zero_candidate():
    r=evaluate(runtime_case(opening=120))
    assert r['ruleResult']['supplyDemand']['candidates']==[]
    assert r['ruleResult']['supplyDemand']['limitations']==['NO_REPLENISHMENT_NEEDED']


@pytest.mark.parametrize('resource',['stock-adjustments','returns','transfers','reservation'])
def test_unsupported_event_types_remain_explicit(resource):
    c=runtime_case();c['movements']['rows'][0]['resource']=resource;r=evaluate(c)
    assert 'STOCK_EVENT_TYPE_UNSUPPORTED' in r['ruleFailureCodes'] and r['ruleResult'] is None


def test_verified_inbound_adds_inventory_once_but_not_effective_supply():
    c=runtime_case();c['inventory']['rows'][0].update(quantity=16,available=16)
    c['movements']['rows'].append(dict(id=999,resource='inbound-orders',record_id=500,inventory_id=7,sku='fixture-sku',warehouse_name='Fixture Warehouse',
        before_quantity=6,after_quantity=16,delta_quantity=10,before_available=6,after_available=16,delta_available=10,
        created_at='2026-11-13T05:30:00+00:00',operation='post',reverses_id=None))
    unproved=evaluate(c);assert 'INBOUND_POSTING_PROOF_MISSING' in unproved['ruleFailureCodes']
    c['inbound_proofs']=[dict(id=500,verified=True,sku='fixture-sku',inventoryId='7',ledgerId='999',postedQuantity='10')]
    r=evaluate(c)
    assert r['inventoryBasis']['status']=='VERIFIED' and r['inventoryBasis']['residual']=='0'
    assert r['ruleResult']['supplyDemand']['baseline']['availableQuantity']=='16'
    assert r['ruleResult']['supplyDemand']['baseline']['inTransitQuantity']=='0'


def test_checkpoint_requires_registered_watermark_and_never_silently_resets_drift():
    c=runtime_case();b=c['opening_binding'].monitor
    cp=StockCheckpoint(version=1,inventoryId='7',quantity='6',available='6',observedAt='2026-11-13T05:10:00+00:00',
        postedAt='2026-11-13T05:00:06+00:00',lastEventId='206',evidenceDigest='a'*64,historyDisposition='Prior history retained, no enterprise clearance')
    c['opening_binding']=SimpleNamespace(monitor=b.model_copy(update={'stockCheckpoint':cp}))
    r=evaluate(c)
    assert r['inventoryBasis']['status']=='VERIFIED' and r['inventoryBasis']['historyStatus']=='ISOLATED_BEFORE_CHECKPOINT'
    c['inventory']['rows'][0].update(quantity=7,available=7)
    assert 'STOCK_MOVEMENT_RECONCILIATION_FAILED' in evaluate(c)['ruleFailureCodes']


@pytest.mark.parametrize('days',[7,15,30])
def test_no_new_event_calendar_simulation_preserves_conservation(days):
    timeline=[]
    for i in range(days+1):
        c=runtime_case(day=(date(2026,11,13)+timedelta(days=i)).isoformat());r=evaluate(c);timeline.append(r)
        assert r['inventoryBasis']['status']=='VERIFIED' and r['inventoryBasis']['residual']=='0'
        assert 'STOCK_SALES_RECONCILIATION_FAILED' not in r['ruleFailureCodes']
    if days>=15:
        assert timeline[-1]['demandWindow']['zeroDays']==7
        assert timeline[-1]['ruleResult']['supplyDemand']['candidates']==[]
    c['scope_complete']=False;unknown=evaluate(c)
    assert unknown['ruleResult'] is None and unknown['demandWindow']['missingDays']==7
    assert unknown['demandWindow']['sampleEnd']=='2026-11-12'


def test_begin_end_business_date_are_distinct_and_old_task_cannot_masquerade_as_today():
    assert business_date('2026-11-13T17:00:00+00:00')==date(2026,11,14)
    assert business_date('2026-11-13T17:00:00+00:00','UTC')==date(2026,11,13)
    c=runtime_case();c['receipt']['completedAt']='2026-11-14T01:00:00+00:00'
    assert 'ACQUISITION_TIME_BOUNDARY_EXPIRED' in evaluate(c)['ruleFailureCodes']


def test_cross_order_reused_outbound_is_not_counted_twice():
    c=runtime_case();c['workflows']['11']=deepcopy(c['workflows']['10']);c['workflows']['11']['order_id']=11
    c['workflows']['11']['shipments'][0]['order_id']=11;c['sales'][1]['item_list'][0]['quantity']=4
    r=evaluate(c)
    assert r['ruleResult'] is None and 'DUPLICATE_FULFILLMENT_EVENT' in r['demandWindow']['issues']


def test_legacy_monitor_serialization_has_no_new_field_or_digest_change():
    c=runtime_case();m=c['opening_binding'].monitor
    assert 'stockCheckpoint' not in m.model_dump(mode='json')
    assert MonitorBinding.model_validate(m.model_dump(mode='json'))==m
