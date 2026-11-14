"""Synthetic business counterexamples, independent from live ERP acceptance."""
from copy import deepcopy
from datetime import datetime,timezone
from decimal import Decimal
import pytest
from tests.support.v2 import SyntheticERP
from commerce_hub.data.sync.v2_catalog import collect_catalog
from commerce_hub.data.projection.v2 import entities
from commerce_hub.scenarios.s01_v2.analysis import analyze,statistics,priority
from commerce_hub.scenarios.s01_v2.products import group_products
from commerce_hub.scenarios.s01_v2.requisition import V2RequisitionService,comparable
from commerce_hub.orchestration.service import TaskError


def fixture(tmp_path,*,stock=6,quotes=True):
    source=SyntheticERP(1)
    source.data['inventory'][0].update(available=stock,quantity=stock)
    source.data['sales']=[dict(id=1,tenant_id=1,order_sn='sales-1',store_name='Synthetic Store',shipping_warehouse='Synthetic Warehouse',
        payment_status='已支付',fulfillment_status='已发货',refund_status='无退款',order_time='2026-11-01 10:00:00',
        item_list=[dict(sku='V2-SKU-0',product_id=1,quantity=10)]),
        dict(id=2,tenant_id=1,order_sn='sales-2',store_name='Synthetic Store',shipping_warehouse='Synthetic Warehouse',
        payment_status='已支付',fulfillment_status='已发货',refund_status='无退款',order_time='2026-11-05 10:00:00',
        item_list=[dict(sku='V2-SKU-0',product_id=1,quantity=10)])]
    if not quotes:source.data['quotes']=[]
    reader=source.reader(tmp_path);reader.state['startedAt']='2026-11-14T01:00:00+00:00'
    catalog=collect_catalog(reader,'1');entity=next(e for e in entities(catalog,'1') if e['warehouseId'])
    return source,reader,catalog,entity


def test_full_history_not_cut_to_week_and_missing_dates_are_not_zero(tmp_path):
    source,reader,c,e=fixture(tmp_path)
    r=analyze(c,e,reader);d=r['decision'];f=d['forecast']
    sales_call=next(params for method,path,params in source.calls if path=='/api/v1/sales-orders')
    assert 'date_from' not in sales_call and 'date_to' not in sales_call
    assert f['totalSales']=='20' and f['observedDays']==2 and f['spanDays']==5 and f['unknownDays']==3
    assert len(f['dailySales'])==2 and f['averageDailyDemand']=='4' and f['salesRecordDayAverage']=='10'
    assert d['status']=='REPLENISH' and d['referenceReplenishmentQuantity']==30
    assert d['purchasableQuantity']==32 and d['stockoutRisk'] is True


def test_no_quotes_or_moq_does_not_block_analysis_or_enable_purchase(tmp_path):
    _,reader,c,e=fixture(tmp_path,quotes=False)
    r=analyze(c,e,reader);d=r['decision']
    assert d['forecast']['available'] and d['referenceReplenishmentQuantity']==50
    assert d['purchasableQuantity'] is None and r['quantity'] is None and not r['procurementEligibility']['eligible']
    with pytest.raises(TaskError):V2RequisitionService.validate_quantity(dict(dataReport=dict(item=r)),50,'')


def test_sufficient_stock_reports_no_replenishment_without_erp(tmp_path):
    _,reader,c,e=fixture(tmp_path,stock=500,quotes=False);c['suggestions']['rows']=[]
    r=analyze(c,e,reader)
    assert r['decision']['status']=='NO_REPLENISHMENT' and r['decision']['referenceReplenishmentQuantity']==0
    assert r['erpComparison']['status']=='ERP_NOT_PROVIDED' and r['erpComparison']['difference'] is None


def test_missing_inventory_keeps_forecast_without_inventing_gap(tmp_path):
    _,reader,c,e=fixture(tmp_path);c['inventory']['rows'][0]['available']=None
    r=analyze(c,e,reader)
    assert r['decision']['forecast']['available'] and r['decision']['referenceReplenishmentQuantity'] is None
    assert r['decision']['status']=='NEEDS_REVIEW' and r['decision']['baseline'] is None


def test_stale_history_remains_estimate_and_stock_is_not_backcalculated(tmp_path):
    _,reader,c,e=fixture(tmp_path)
    r=analyze(c,e,reader)
    assert 'STALE_SALES_SAMPLES' in r['decision']['forecast']['risks']
    assert r['inventory']['historicalReconciliation']=='NOT_ASSERTED'
    reader.state['startedAt']='2026-11-15T01:00:00+00:00';c['businessDate']='2026-11-15'
    next_day=analyze(c,e,reader)
    assert next_day['decision']['referenceReplenishmentQuantity']==r['decision']['referenceReplenishmentQuantity']


@pytest.mark.parametrize('field,value',[('payment_status','未支付'),('fulfillment_status','未发货'),('refund_status','已退款')])
def test_invalid_sales_state_excluded_not_used_as_zero(tmp_path,field,value):
    _,reader,c,e=fixture(tmp_path);c['sales']['rows'][0][field]=value
    r=analyze(c,e,reader)
    assert r['decision']['forecast']['totalSales']=='10'
    assert r['decision']['forecast']['excluded']['SALES_NOT_NET_FULFILLED']==1


def test_duplicate_conflict_does_not_silently_add_sales(tmp_path):
    _,reader,c,e=fixture(tmp_path);duplicate=deepcopy(c['sales']['rows'][0]);duplicate['item_list'][0]['quantity']=999
    c['sales']['rows'].append(duplicate)
    assert not analyze(c,e,reader)['decision']['forecast']['available']


def test_store_warehouse_isolation_sku_counts_and_comparison(tmp_path):
    _,reader,c,e=fixture(tmp_path);first=analyze(c,e,reader)
    second=deepcopy(first);second['entityKey']='b'*64;second['warehouseId']='2';second['decision']['status']='NO_REPLENISHMENT';second['decision']['referenceReplenishmentQuantity']=0;second['decision']['stockoutRisk']=False
    stats=statistics([first,second],'product-counts-v1');groups=group_products([first,second],priority)
    assert stats['discoveredSkuCount']==stats['judgedSkuCount']==stats['replenishSkuCount']==1
    assert stats['scopeObjectCount']==stats['judgedScopeCount']==2 and stats['replenishScopeCount']==1
    assert stats['noReplenishmentSkuCount']==0 and groups[0]['productSummary']['scopeCount']==2
    assert first['erpComparison']['difference']==30-120
    other=deepcopy(c['sales']['rows'][0]);other['id']=3;other['shipping_warehouse']='Other warehouse';other['item_list'][0]['quantity']=999
    c['sales']['rows'].append(other)
    assert analyze(c,e,reader)['decision']['forecast']['totalSales']=='20'


def test_unknown_in_transit_not_deducted_and_moq_stays_enforced(tmp_path):
    _,reader,c,e=fixture(tmp_path)
    c['formalPurchases']['rows']=[dict(id=8,status_text='待到货',warehouse_name='Synthetic Warehouse',item_list=[dict(sku=e['sku'],quantity=500,received_qty=0)])]
    r=analyze(c,e,reader)
    assert r['decision']['referenceReplenishmentQuantity']==30 and r['decision']['confirmedSupplyQuantity'] is None
    with pytest.raises(TaskError):V2RequisitionService.validate_quantity(dict(dataReport=dict(item=r)),30,'')
    assert 'SAME_SCOPE_FORMAL_PURCHASE_REQUIRES_REVIEW' in r['procurementEligibility']['hardBlocks']
    with pytest.raises(TaskError):V2RequisitionService.validate_quantity(dict(dataReport=dict(item=r)),32,'')


@pytest.mark.parametrize('complete',[True,False])
def test_pending_purchase_blocks_duplicate_without_erasing_reference_demand(tmp_path,complete):
    _,reader,c,e=fixture(tmp_path)
    c['pendingPurchases']=dict(complete=complete,rows=[dict(id=88,status_text='待审核',order_sn='fixture-pending',
        warehouse_name='Synthetic Warehouse',item_list=[dict(sku=e['sku'],quantity=32)])] if complete else [])
    r=analyze(c,e,reader)
    code='SAME_SCOPE_PENDING_REQUISITION' if complete else 'PENDING_PURCHASE_QUERY_INCOMPLETE'
    assert code in r['procurementEligibility']['hardBlocks']
    assert r['decision']['referenceReplenishmentQuantity']==30 and r['decision']['forecast']['available']
    assert r['decision']['confirmedSupplyQuantity'] is None and not r['procurementEligibility']['eligible']


def test_comparison_ambiguous_and_revalidation_ignores_observation_identity(tmp_path):
    _,reader,c,e=fixture(tmp_path);first=analyze(c,e,reader)
    reader.state['startedAt']='2026-11-14T02:00:00+00:00';second=analyze(c,e,reader)
    assert comparable(first)==comparable(second)
    c['suggestions']['rows'].append(dict(c['suggestions']['rows'][0],id=999));e['suggestionIds'].append('999')
    assert analyze(c,e,reader)['erpComparison']['difference'] is None


def test_report_ratio_accepts_mysql_double_rounding_but_rejects_changed_counts():
    from commerce_hub.scenarios.s01_v2.handler import summary_matches
    expected=dict(coverage=10/11,decisionCoverage=10/11,processedCount=11)
    saved=dict(expected,coverage=0.9090909090909092,decisionCoverage=0.9090909090909092)
    assert summary_matches(saved,expected)
    assert not summary_matches(dict(saved,processedCount=12),expected)
    assert not summary_matches(dict(saved,coverage=0.9091),expected)
    assert not summary_matches(dict(saved,extra=0),expected)


def test_partial_product_batch_can_sort_pending_and_review_rows(tmp_path):
    from commerce_hub.scenarios.s01_v2.analysis import priority
    _,reader,c,e=fixture(tmp_path);r=analyze(c,e,reader)
    r['decision']['status']='NEEDS_REVIEW';r['decision']['stockoutRisk']=False
    pending=dict(entityKey='pending',sku='PENDING',sourceGrade='UNAVAILABLE',analysisState='PENDING')
    assert len(sorted([pending,r],key=priority))==2


def test_legacy_zero_quantity_ai_facts_remain_compatible_with_sealed_reports(tmp_path):
    from commerce_hub.scenarios.s01_v2.explanation import bundle
    _,reader,c,e=fixture(tmp_path);item=analyze(c,e,reader)
    item.pop('decisionVersion');item.pop('decision');item.pop('explanationVersion');item['quantity']=None
    binding=dict(taskRef=dict(tenantId='fixture',taskId='old-task'),planVersion='1',snapshotId=item['ruleResult']['snapshotId'],participantId='s01')
    fact=next(f for f in bundle(item,binding).context.facts if f.ref=='quantity')
    assert fact.allowedPhrases==['当前没有可靠的正数量建议，不能将零值或缺失解释为无需补货']
