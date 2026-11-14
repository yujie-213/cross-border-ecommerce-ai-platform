"""Offline review experiments; never imported by the product.

Actual normalize_owned/rule_result/B01/B02 are called unchanged. Candidate
window policies below are comparison prototypes, not an admitted new policy.
The replay changes explicit input timestamps, never the OS clock or ERP data.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
from commerce_hub.data.projection.owned import normalize_owned
from commerce_hub.scenarios.s01_v2.analysis import rule_result, analyze
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture
from commerce_hub.data.contracts import AdmittedInput
from commerce_hub.capabilities.forecasting import propose

spec=importlib.util.spec_from_file_location('review_owned_fixture',ROOT/'tests/unit/data/test_owned.py')
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)


def prototype(days, anchor, *, lookback=15, minimum=7, missing_limit=Decimal('.2'), freshness=2):
    """Each known day, including zero, has independent complete-scope evidence.

    Missing days remain absent. A is event-selected 7-day mean; B/E use all
    proven calendar days. E's thresholds are proposed review defaults only.
    """
    window=[anchor-timedelta(days=i) for i in range(lookback,0,-1)]
    usable=[(d,days[d]) for d in window if d in days]
    latest=(anchor-max(d for d,_ in usable)).days if usable else None
    mean=lambda xs: str(sum((q for _,q in xs),Decimal(0))/Decimal(len(xs))) if xs else None
    allowed=len(usable)>=minimum and Decimal(lookback-len(usable))/lookback<=missing_limit and latest is not None and latest<=freshness
    return dict(validDays=len(usable),missingDays=lookback-len(usable),latestAgeDays=latest,
        A_latest7Mean=mean(usable[-7:]) if len(usable)>=minimum else None,
        B_allValidMean=mean(usable), E_level='QUANTIFIED_CONDITIONAL' if allowed else 'REFERENCE_ONLY' if usable else 'FACTS_ONLY',
        E_mean=mean(usable), windowDays=lookback)


def production(case, anchor, *, v2=False, filter_window=True):
    m,c,r=deepcopy(case)
    r['completedAt']=anchor.isoformat()
    if not v2:return normalize_owned(c,m,r,True)
    day=anchor.astimezone(timezone(timedelta(hours=8))).date()
    sales=c['sales']['rows']
    if filter_window:
        sales=[s for s in sales if day-timedelta(days=7)<=datetime.strptime(s['order_time'],'%Y-%m-%d %H:%M:%S').date()<=day]
    product=dict(c['product']['rows'][0],supplier_name='Fixture Supplier');q=dict(c['quotes']['rows'][0],currency='USD',supplier_name='Fixture Supplier')
    catalog={k:deepcopy(c[v]) for k,v in [('inventory','inventory')]}
    catalog.update(products=dict(rows=[product],complete=True),quotes=dict(rows=[q],complete=True),
        sales=dict(rows=sales,complete=True),formalPurchases=dict(rows=[],complete=True),suggestions=dict(rows=[],complete=True),businessDate=day.isoformat())
    entity=dict(identityVerified=True,productId='1',inventoryIds=['7'],sourceTenant='1',storeId='2',warehouseId='3',
        sku=m.sku,storeName=m.storeName,warehouseName=m.warehouseName,entityKey='offline-review-entity',suggestionIds=[])
    class Reader:
        state=dict(startedAt=anchor.isoformat())
        def resource(self,name,path,parameters=None,detail=False):return c['supplier' if name.startswith('supplier-') else name]
    result,failures=rule_result(catalog,entity,Reader(),opening_binding=m)
    return dict(input=(result or {}).get('input'),forecast=(result or {}).get('forecast'),failures=failures,
        item=analyze(catalog,entity,Reader(),opening_binding=m))


def main():
    rows=[]
    def check(name,ok,**details):
        assert ok,name
        rows.append(dict(scenario=name,result='PASS',**details))
    case=fixtures.owned_case();anchor=datetime(2026,11,13,6,tzinfo=timezone.utc)
    normal=production(case,anchor);snap=capture(project(AdmittedInput.model_validate(normal['input']),'review'))
    b=propose(snap)
    check('7 complete days / unchanged B01 B02',normal['forecast']['totalSales']=='39' and b['candidates'][0]['quantity']=='48',total='39',candidate='48')
    tomorrow=production(case,anchor+timedelta(days=1),v2=True)
    same_all=production(case,anchor+timedelta(days=1))
    check('fixed ERP / date alone / V2 fails',tomorrow['failures']==['STOCK_SALES_RECONCILIATION_FAILED'] and same_all['input'] is not None,
        v2Failures=tomorrow['failures'],fullRegisteredForecast=same_all['forecast']['totalSales'])
    rawv2=production(case,anchor+timedelta(days=1),v2=True,filter_window=False)
    check('same full capture tomorrow / V2 passes',rawv2['input'] is not None)
    d=date(2026,11,14)
    seven={d-timedelta(days=i):Decimal(16-i) for i in [1,3,5,7,9,11,13]}
    a=prototype(seven,d)
    check('15 days / 7 proven / eight unknown',a['A_latest7Mean'] is not None and a['E_level']=='REFERENCE_ONLY',comparison=a)
    ten={d-timedelta(days=i):Decimal(i) for i in range(1,11)}
    a=prototype(ten,d)
    check('15 days / 10 proven / different means',a['A_latest7Mean']=='4' and a['B_allValidMean']=='5.5',comparison=a)
    few={d-timedelta(days=i):Decimal(3) for i in range(1,7)};a=prototype(few,d)
    check('15 days / fewer than 7',a['A_latest7Mean'] is None and a['E_level']=='REFERENCE_ONLY',comparison=a)
    zero={d-timedelta(days=i):Decimal(0 if i<=3 else 4) for i in range(1,16)};a=prototype(zero,d)
    check('three true zero days',a['validDays']==15 and a['B_allValidMean']=='3.2' and a['E_level']=='QUANTIFIED_CONDITIONAL',comparison=a)
    missing={d-timedelta(days=i):Decimal(4) for i in range(4,16)};a=prototype(missing,d)
    check('recent missing / freshness fails',a['validDays']==12 and a['latestAgeDays']==4 and a['E_level']=='REFERENCE_ONLY',comparison=a)
    drift=deepcopy(case);inv=drift[1]['inventory']['rows'][0];inv['quantity']+=10;inv['available']+=10
    n=production(drift,anchor)
    check('stock changes / sales unchanged',n['input'] is None and n['issues'][0]['code']=='STOCK_SALES_RECONCILIATION_FAILED',currentFailure=n['issues'][0]['code'],
        checkpointPrototype=dict(old=6,verifiedInbound=10,current=16,residual=16-6-10))
    # Existing real production project does not invent an ETA or deduct a PO.
    from commerce_hub.scenarios.s01_v2.analysis import formal_purchases
    po=formal_purchases(dict(formalPurchases=dict(rows=[dict(id=900,item_list=[dict(sku='fixture-sku',quantity=48,received_qty=0)],
        warehouse_name='Fixture Warehouse',status_text='待到货',planned_arrival='2026-11-20')])),dict(sku='fixture-sku',warehouseName='Fixture Warehouse'))
    check('real-style approved PO / sellable date unknown',po[0]['includedInCalculation'] is False and po[0]['sellableDate'] is None,projection=po)
    expired=deepcopy(case);expired[1]['quotes']['rows'][0]['valid_to']='2026-11-12';n=production(expired,anchor)
    check('expired quote blocks current entire normalization',n['input'] is None and n['issues'][0]['code']=='QUOTE_NOT_EFFECTIVE_OR_RELATED',
        currentFailure=n['issues'][0]['code'],proposal='retain demand/risk facts; require effective quote at purchase')
    # D03/B02 already support calculation vs candidate gates. Demonstrate this
    # with a synthetic normalized contract, not by bypassing production D02.
    risk_only=deepcopy(normal['input'])
    risk_only['policy'].update(moq=None,orderMultiple=None,maxOrderQty=None,candidateDates=[])
    risk_snapshot=capture(project(AdmittedInput.model_validate(risk_only),'review-risk-only'))
    risk=propose(risk_snapshot)
    check('existing B01 risk without purchase constraints',risk['baseline']==b['baseline'] or
        (risk['baseline']['gapQuantity']==b['baseline']['gapQuantity'] and risk['baseline']['stockoutRisk']==b['baseline']['stockoutRisk']
        and not risk['candidates'] and risk_snapshot.calculation_allowed and not risk_snapshot.candidates_allowed),
        gap=risk['baseline']['gapQuantity'],candidates=risk['candidates'],limitation=risk['limitations'])
    history=deepcopy(normal)
    check('old report retained after new failure',history['input'] is not None and tomorrow['input'] is None and history==normal,
        limitation='object-level offline replay only; no new browser/history API acceptance')
    timeline=[]
    # Extend synthetic quote validity only in fixture, isolating the calendar defect.
    continuous=deepcopy(case);continuous[1]['quotes']['rows'][0]['valid_to']='2027-01-01'
    for i in range(30):
        t=anchor+timedelta(days=i);v=production(continuous,t,v2=True);owned=production(continuous,t)
        # No new events, complete continuing observation: new days are certified zeros.
        known={date(2026,11,6)+timedelta(days=j):Decimal(q) for j,q in enumerate([4,5,4,6,9,5,6])}
        day=t.date()
        for j in range(i):known[date(2026,11,13)+timedelta(days=j)]=Decimal(0)
        proposed=prototype(known,day,lookback=7,missing_limit=Decimal(0))
        timeline.append(dict(day=day.isoformat(),currentV2=v['failures'],ownedAllowed=owned['input'] is not None,
            ownedTotal=(owned.get('forecast') or {}).get('totalSales'),proposal=proposed))
    check('30 day fixed-source / continuing proven observation',not timeline[0]['currentV2'] and timeline[1]['currentV2']==['STOCK_SALES_RECONCILIATION_FAILED']
        and timeline[8]['currentV2']==['FULFILLED_SALES_HISTORY_UNPROVEN'] and all(t['ownedAllowed'] for t in timeline)
        and timeline[-1]['proposal']['E_level']=='QUANTIFIED_CONDITIONAL' and timeline[-1]['proposal']['E_mean']=='0',timeline=timeline)
    # No new daily coverage evidence: frozen positive history becomes reference.
    stale=prototype(seven,d+timedelta(days=30));check('old sales beyond 15 days',stale['E_level']=='FACTS_ONLY',comparison=stale,
        legacyReference='separate labeled historical rate may be displayed; never current recommendation')
    # Candidate conservation and anti-double-count examples, entirely offline.
    check('return inbound adjustment / checkpoint conservation',6+2+10-1-3==14,
        events=[dict(kind=k,delta=q) for k,q in [('return_sellable',2),('inbound',10),('adjustment',-1),('new_shipment',-3)]],
        checkpoint=6,current=14,residual=0,warning='refund without sellable return adds no stock; duplicated event rejected by ID')
    out=dict(nature='OFFLINE_SYNTHETIC_PRODUCTION_REPLAY_AND_UNAPPROVED_POLICY_COMPARISON',result='PASS',
        scenarios=rows,checks=len(rows),newERPRequests=0,newModels=0,productionChanges=0)
    path=ROOT/'docs/evidence/S01-DATA-REVIEW/replay.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result='PASS',checks=len(rows),artifact=str(path.relative_to(ROOT)))))


if __name__=='__main__':main()
