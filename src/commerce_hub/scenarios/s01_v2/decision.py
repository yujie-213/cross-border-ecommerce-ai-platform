"""Independent business decisions using D02 estimates and unchanged B01/B02."""
from copy import deepcopy
from datetime import date,datetime,timedelta
from decimal import Decimal,ROUND_CEILING
from commerce_hub.data.contracts import AdmittedInput,fingerprint
from commerce_hub.data.projection import project
from commerce_hub.data.projection.demand_reference import sales_reference,VERSION
from commerce_hub.data.quality import capture
from commerce_hub.capabilities.metrics import evaluate
from commerce_hub.capabilities.forecasting import propose


def snapshot_for(entity,observed,day,available,rate,horizon,c):
    daily=Decimal(rate)
    # Round cumulative demand, then difference adjacent totals. Rounding every
    # daily fraction upward would turn an exact 39-unit week into 39.00000006
    # and incorrectly request one extra whole unit after ceiling the gap.
    totals=[(daily*i).quantize(Decimal('.00000001')) for i in range(horizon+1)]
    key=dict(sku=entity['sku'],store=entity['storeId'],warehouse=entity['warehouseId'])
    digest=fingerprint([entity['entityKey'],observed.isoformat(),str(daily),horizon])
    lead=c.get('leadDays');arrival=max(1,lead) if type(lead) is int and 0<=lead<horizon else 1
    value=AdmittedInput(sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',fixtureId='decision-'+digest[:32],
        provenanceRef='decision-'+digest[:32],rulesRef=VERSION,asOf=observed,businessDate=day,coverageComplete=True,
        mapping=dict(version=VERSION,sourceSku=key['sku'],sourceStore=key['store'],sourceWarehouse=key['warehouse'],
            canonicalSkuId=key['sku'],storeId=key['store'],warehouseId=key['warehouse'],sourceUnit='EA',unit='EA',unitsPerSourceUnit='1'),
        inventory=[dict(recordId='observed-stock',**key,unit='EA',availableQty=str(available),semantics='NET_AVAILABLE',sourceUpdatedAt=observed)],
        demand=[dict(recordId='reference-'+str(i),**key,unit='EA',day=day+timedelta(days=i),quantity=str(totals[i]-totals[i-1]),semantics='INCREMENTAL_EXCLUDES_RESERVED') for i in range(1,horizon+1)],
        supply=[],policy=dict(version=VERSION,horizonDays=horizon,bufferDays=0,maxAgeHours=24,moq=c.get('moq'),orderMultiple=c.get('orderMultiple'),
            candidateDates=[day+timedelta(days=arrival)] if type(lead) is int else [],maxOrderQty='100000',
            otherConstraints='UNCONFIRMED',qualityDisposition='UNKNOWN',advisoryOnly=True))
    return capture(project(value,'decision-'+digest[:32]))


def comparison(catalog,entity,ours,integer):
    records=[s for s in catalog['suggestions']['rows'] if str(s['id']) in entity['suggestionIds']]
    valid=len(records)==1 and catalog['suggestions']['complete']
    source=records[0] if valid else None;n=integer(source.get('suggested_qty'),zero=True) if source else None
    matched=entity.get('identityVerified') and entity.get('warehouseId') is not None
    status='COMPARABLE' if matched and n is not None and ours is not None else 'ERP_NOT_PROVIDED' if not records else 'ERP_AMBIGUOUS' if len(records)>1 else 'SCOPE_OR_BASIS_UNCONFIRMED'
    delta=ours-n if status=='COMPARABLE' else None
    return dict(status=status,platformQuantity=ours,erpQuantity=n,difference=delta,
        significant=delta is not None and abs(delta)>=max(5,(n or 0)*.2),recordCount=len(records),
        records=[{k:s.get(k) for k in ['id','recommendation_no','suggested_qty','daily_sales','updated_at','stockout_date','urgency']} for s in records],
        explanation='平台按已披露历史样本、当前可用库存及规划周期独立试算；ERP算法、窗口和在途抵扣口径未知，无法确认差异成因。' if records else 'ERP 未提供适用建议，平台分析独立进行。'),source,n


def analyze_decision(catalog,entity,reader,*,requisition_authorized=None):
    from .analysis import constraints,formal_purchases,integer
    result=deepcopy(entity);c,q,product=constraints(catalog,entity);history=sales_reference(catalog,entity)
    stock=[r for r in catalog['inventory']['rows'] if str(r['id']) in entity['inventoryIds']]
    available=stock[0].get('available') if entity['identityVerified'] and catalog['inventory']['complete'] and len(stock)==1 else None
    if type(available) is not int or available<0:available=None
    lead=c['leadDays'];lead_known=type(lead) is int and 0<=lead<=24
    horizon=max(1,lead+7) if lead_known else 14
    day=date.fromisoformat(catalog['businessDate']);observed=datetime.fromisoformat(reader.state['startedAt'])
    assumption=['未来需求延续已观察历史，参考估计不能保证未来销量。','各店仓独立计算；未知在途未抵扣，正式采购需人工核对。',
        '主规划周期为有效报价交期加7天补货覆盖。' if lead_known else '未获可靠交期，主试算采用14天规划周期；不是已确认交期。']
    baseline=None;rules=None;ref=None;purchase=None;scenarios=[]
    if history.get('available'):
        assumption.append(history['assumption'])
        for period in sorted({7,14,30,horizon}):
            demand=Decimal(history['averageDailyDemand'])*period
            high=Decimal(history['salesRecordDayAverage'])*period
            row=dict(days=period,forecastQuantity=str(demand),recordDayScenarioQuantity=str(high),referenceReplenishmentQuantity=None)
            if available is not None and c['unit']=='EA':
                snap=snapshot_for(entity,observed,day,available,history['averageDailyDemand'],period,c)
                metrics=evaluate(snap);row.update(referenceReplenishmentQuantity=int(Decimal(metrics['gapQuantity']).to_integral_value(rounding=ROUND_CEILING)))
                if period==horizon:
                    baseline=metrics;ref=row['referenceReplenishmentQuantity']
                    if not c['hardBlocks'] and lead_known:
                        supplied=propose(snap);candidate=next(iter(supplied['candidates']),None)
                        if candidate:purchase=integer(candidate['quantity'])
                        rules=dict(supplyDemand=supplied,forecast=dict(history,observationDays=history['observedDays'],windowStart=history['sampleStart'],windowEnd=history['sampleEnd'],
                            calculationHorizonDays=horizon,leadDays=lead,coverageDays=7,forecastDays=horizon,forecastQuantity=str(demand)),snapshotId=snap.snapshotId)
            scenarios.append(row)
    status='REPLENISH' if ref is not None and ref>0 else 'NO_REPLENISHMENT' if ref==0 else 'NEEDS_REVIEW'
    risk=bool(baseline and baseline['stockoutRisk'])
    explanation=[]
    if history.get('available'):
        explanation.append(f"已读取{history['orderCount']}条可信销售记录，{history['observedDays']}个有记录日期共{history['totalSales']}件；首末记录跨度{history['spanDays']}天。")
        explanation.append(f"区间参考需求约{Decimal(history['averageDailyDemand']):.2f}件/天；仅有销售记录日均{Decimal(history['salesRecordDayAverage']):.2f}件/天，两者口径不同。")
    else:explanation.append('缺少可归属该店仓的可信已支付、已发货、无退款历史，暂不能预测需求。')
    if baseline:
        explanation.append(f"当前可用库存{available}件，按{horizon}天周期需求约{Decimal(baseline['targetQuantity']):.2f}件，参考补充{ref}件，未扣未核实在途。" if ref else f"当前可用库存{available}件覆盖{horizon}天参考需求，暂不补货；仍需关注需求变化。")
    elif history.get('available'):explanation.append('需求预测已生成，库存数量、单位或店仓关系尚未充分确认，因此不输出库存缺口。')
    if history.get('sampleAgeDays',0)>7:explanation.append(f"最近可信销量距今{history['sampleAgeDays']}天，历史偏旧，请核实近期需求是否变化。")
    if risk and lead_known and baseline.get('coverageDays') is not None and Decimal(baseline['coverageDays'])<lead:
        explanation.append('库存覆盖短于报价交期，普通到货可能无法消除提前缺货，应优先核实加急或调拨条件。')
    compare,source,n=comparison(catalog,entity,ref,integer)
    hard=list(c['hardBlocks'])
    if not catalog['inventory']['complete']:hard.append('INVENTORY_QUERY_INCOMPLETE')
    if not purchase:hard.append('NO_POSITIVE_RECOMMENDATION_BASIS')
    if not lead_known:hard.append('PROCUREMENT_LEAD_UNCONFIRMED')
    formal=formal_purchases(catalog,entity)
    pending=[]
    for p in catalog.get('pendingPurchases',{}).get('rows',[]):
        if p.get('warehouse_name')==entity['warehouseName'] and any(l.get('sku')==entity['sku'] for l in p.get('item_list',[])):
            pending.append(dict(erpId=str(p['id']),erpNumber=p.get('order_sn'),status=p.get('status_text'),
                warehouseName=p.get('warehouse_name'),purpose='SALES_REPLENISHMENT' if 'SALES_REPLENISHMENT' in (p.get('remark') or '') else 'UNCONFIRMED',
                includedInCalculation=False))
    if catalog.get('pendingPurchases',{}).get('complete') is False:hard.append('PENDING_PURCHASE_QUERY_INCOMPLETE')
    if pending:hard.append('SAME_SCOPE_PENDING_REQUISITION')
    if any(p['warehouseMatch'] for p in formal):hard.append('SAME_SCOPE_FORMAL_PURCHASE_REQUIRES_REVIEW')
    if source and any(p.get('sourcePlanNumber')==source.get('recommendation_no') and p['warehouseMatch'] for p in formal):hard.append('KNOWN_FORMAL_PURCHASE_FOR_SOURCE_PLAN')
    # Preserve Scheme B for an independently matched positive ERP suggestion;
    # it is a procurement source, never the platform's own demand forecast.
    grade='PLATFORM_REFERENCE' if ref is not None else 'DEMAND_REFERENCE' if history.get('available') else 'UNAVAILABLE'
    quantity=purchase
    if ref is None and n and entity['identityVerified']:
        grade='REFERENCE_ONLY';quantity=n
        hard=[x for x in hard if x not in {'NO_POSITIVE_RECOMMENDATION_BASIS','PROCUREMENT_LEAD_UNCONFIRMED'}]
    elif ref is None and n==0:grade='REFERENCE_ONLY'
    elif ref is None and compare['recordCount']:grade='UNVERIFIED'
    warnings=['NO_ATOMIC_CROSS_INTERFACE_SNAPSHOT','FORMAL_PURCHASE_DEDUCTION_UNCONFIRMED']+history.get('risks',[])
    if compare['recordCount']:warnings+=['ERP_ALGORITHM_UNKNOWN','ERP_DAILY_SALES_WINDOW_UNKNOWN','ERP_GENERATION_TIME_UNVERIFIED','ERP_PURCHASE_NETTING_UNKNOWN']
    if any(not p['warehouseMatch'] for p in formal):warnings.append('RELATED_PURCHASE_TARGETS_DIFFERENT_WAREHOUSE')
    eligible=not hard
    result.update(explanationVersion='s01-product-experience-v1',decisionVersion=VERSION,decision=dict(status=status,forecast=history,horizonDays=horizon,leadDays=lead if lead_known else None,
        horizonBasis='QUOTE_LEAD_PLUS_7' if lead_known else 'ASSUMED_14_DAY_PLANNING',forecastQuantity=next((s['forecastQuantity'] for s in scenarios if s['days']==horizon),None),
        referenceReplenishmentQuantity=ref,purchasableQuantity=purchase,confirmedSupplyQuantity=None,
        supplyBasis='UNVERIFIED_SUPPLY_NOT_DEDUCTED',stockoutRisk=risk,coverageDays=baseline['coverageDays'] if baseline else None,
        firstShortageDate=baseline['firstShortageDate'] if baseline else None,confidence=history.get('confidence','INSUFFICIENT'),
        assumptions=assumption,explanation=explanation,scenarios=scenarios,baseline=baseline),erpComparison=compare,
        analysisState='ANALYZED' if status=='REPLENISH' else 'NO_REPLENISHMENT' if status=='NO_REPLENISHMENT' else 'ERP_REFERENCE' if quantity else 'HISTORICAL_REFERENCE' if history.get('available') else 'NEEDS_REVIEW',
        sourceGrade=grade,quantity=quantity,sourceQuantity=n,unit=c['unit'],constraints=c,formalPurchases=formal,pendingPurchases=pending,
        inventory=dict(available=available,inventoryIds=entity['inventoryIds'],warehouseId=entity['warehouseId'],
            sourceUpdatedAt=stock[0].get('updated_at') if len(stock)==1 else None,basis='CURRENT_ERP_AVAILABLE_FIELD',historicalReconciliation='NOT_ASSERTED'),
        uncertainties=warnings,ruleFailureCodes=[],ruleResult=rules,sourceSuggestion=source,sourceSuggestionCount=compare['recordCount'],sourceSuggestions=compare['records'],
        riskGroup='RULE_CONFIRMED' if risk else 'NO_REPLENISHMENT' if status=='NO_REPLENISHMENT' else 'UNVERIFIED',riskDate=baseline['firstShortageDate'] if baseline else None,
        sourceUrgency=source.get('urgency') if source else None,observedAt=reader.state['startedAt'],
        procurementEligibility=dict(eligible=eligible,hardBlocks=sorted(set(hard)),warnings=warnings,scopeAuthorized=bool(requisition_authorized),policyVersion='s01-product-procurement-v1'))
    return result
