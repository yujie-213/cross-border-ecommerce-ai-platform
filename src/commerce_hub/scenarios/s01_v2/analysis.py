"""Dual channel result; source reliability and procurement eligibility are independent."""
from copy import deepcopy
from datetime import date,datetime
from decimal import Decimal,InvalidOperation
from types import SimpleNamespace
from commerce_hub.data.contracts import fingerprint,AdmittedInput
from commerce_hub.data.projection.owned import normalize_owned
from commerce_hub.data.projection.monitor import ForecastPolicy
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture
from commerce_hub.capabilities.forecasting import propose

REFERENCE_NOTICE='该补货数量来自 ERP 现有建议记录，部分计算依据未验证。请核对采购条件及已有采购后人工确认。'


def integer(value,*,zero=False):
    if isinstance(value,bool) or value is None:return None
    try:
        n=Decimal(str(value))
        return int(n) if n.is_finite() and n==n.to_integral_value() and (0 if zero else 1)<=n<=100000000 else None
    except (ValueError,InvalidOperation):return None


def matching_sales(catalog,entity):
    return [s for s in catalog['sales']['rows'] if s.get('store_name')==entity['storeName'] and s.get('shipping_warehouse')==entity['warehouseName']
        and any(l.get('sku')==entity['sku'] for l in s.get('item_list',[]))]


def constraints(catalog,entity):
    product=next((p for p in catalog['products']['rows'] if str(p['id'])==entity['productId']),{})
    day=catalog['businessDate'];issues=[]
    if not entity['identityVerified']:issues.append('BUSINESS_SCOPE_UNRESOLVED')
    stock=[r for r in catalog['inventory']['rows'] if str(r['id']) in entity['inventoryIds']]
    if len(stock)!=1:issues.append('INVENTORY_BUCKET_RELATION_UNCONFIRMED')
    elif type(stock[0].get('available')) is not int or stock[0]['available']<0:issues.append('INVENTORY_QUANTITY_UNCONFIRMED')
    unit='EA' if product.get('unit') in {'piece','件','EA'} else None
    if not unit:issues.append('PROCUREMENT_UNIT_UNCONFIRMED')
    multiple=integer(product.get('default_carton_qty'))
    if not multiple:issues.append('CARTON_QUANTITY_MISSING_OR_INVALID')
    quotes=[q for q in catalog['quotes']['rows'] if str(q.get('product_id'))==entity['productId'] and q.get('sku')==entity['sku']
        and q.get('enabled') is True and q.get('status')=='effective' and str(q.get('valid_from','9999'))<=day<=str(q.get('valid_to',''))]
    if product.get('supplier_name'):
        quotes=[q for q in quotes if q.get('supplier_name')==product['supplier_name']]
    elif not quotes:issues.append('SUPPLIER_RELATION_MISSING')
    if len(quotes)!=1:issues.append('EFFECTIVE_QUOTE_MISSING_OR_AMBIGUOUS')
    quote=quotes[0] if len(quotes)==1 else None
    if quote:
        moq=integer(quote.get('minimum_quantity'))
        if not integer(quote.get('supplier_id')):issues.append('SUPPLIER_RELATION_MISSING')
        try:
            price=Decimal(str(quote['unit_price']));minimum=Decimal(str(quote['minimum_amount']))
            if not price.is_finite() or not minimum.is_finite() or price<=0 or minimum<0:raise ValueError()
        except (ValueError,KeyError,ArithmeticError):price=minimum=None;issues.append('QUOTE_PRICE_INVALID')
        if not moq:issues.append('QUOTE_MOQ_INVALID')
        if quote.get('currency') not in {'USD','CNY','EUR','GBP'}:issues.append('QUOTE_CURRENCY_UNCONFIRMED')
    else:moq=price=minimum=None
    if not catalog['quotes']['complete']:issues.append('QUOTE_QUERY_INCOMPLETE')
    if not catalog['formalPurchases']['complete']:issues.append('FORMAL_PURCHASE_QUERY_INCOMPLETE')
    return dict(unit=unit,moq=moq,orderMultiple=multiple,quoteId=str(quote['id']) if quote else None,
        supplierId=str(quote['supplier_id']) if quote else None,unitPrice=str(price) if price is not None else None,
        minimumAmount=str(minimum) if minimum is not None else None,currency=quote.get('currency') if quote else None,
        supplierName=quote.get('supplier_name') if quote else None,quoteNo=quote.get('quote_no') if quote else None,
        quoteVersion=quote.get('version') if quote else None,quoteValidFrom=quote.get('valid_from') if quote else None,quoteValidTo=quote.get('valid_to') if quote else None,
        leadDays=quote.get('lead_days') if quote else None,hardBlocks=sorted(set(issues))),quote,product


def formal_purchases(catalog,entity):
    result=[]
    for p in catalog['formalPurchases']['rows']:
        lines=p.get('item_list',[])
        for index,line in enumerate(lines):
            if line.get('sku')!=entity['sku']:continue
            received=line.get('received_qty',p.get('received_qty') if len(lines)==1 else None)
            ordered=integer(line.get('quantity'),zero=True);got=integer(received,zero=True)
            result.append(dict(erpId=str(p['id']),erpNumber=p.get('order_sn'),lineIndex=index,sku=entity['sku'],status=p.get('status_text'),
                orderedQuantity=ordered,receivedQuantity=got,unreceivedQuantity=ordered-got if ordered is not None and got is not None and got<=ordered else None,
                plannedArrival=p.get('planned_arrival'),sellableDate=None,includedInCalculation=False,effectiveSupplyQuantity=None,
                warehouseName=p.get('warehouse_name'),warehouseMatch=p.get('warehouse_name')==entity['warehouseName'],
                storeAttribution='UNKNOWN_SOURCE_HAS_NO_STORE_FK',sourcePlanNumber=p.get('source_plan_no')))
    return result


def rule_result(catalog,entity,reader,*,opening_binding=None):
    """Uses the unchanged owned normalizer/quality/B02. No second supply formula."""
    c,q,p=constraints(catalog,entity)
    if c['hardBlocks']:return None,['RULE_CONSTRAINTS_INCOMPLETE']
    if not catalog['sales']['complete'] or not catalog['inventory']['complete']:return None,['RULE_HISTORY_COVERAGE_INCOMPLETE']
    sales=matching_sales(catalog,entity)
    # Unfulfilled/old legacy rows cannot satisfy the original strict rule contract.
    if not sales:return None,['FULFILLED_SALES_HISTORY_UNPROVEN']
    if any(s.get('fulfillment_status')!='已发货' or s.get('payment_status')!='已支付' or s.get('refund_status')!='无退款' for s in sales):
        return None,['SALES_NOT_NET_FULFILLED']
    inv=[r for r in catalog['inventory']['rows'] if str(r['id']) in entity['inventoryIds']]
    captures={name:dict(rows=rows,complete=True,total=len(rows)) for name,rows in [
        ('product',[dict(p,unit='piece')]),('inventory',inv),('sales',sales),('quotes',[q]),('purchases',[])]}
    supplier=reader.resource('supplier-'+str(q['supplier_id']),'/api/v1/suppliers/'+str(q['supplier_id']),detail=True)
    captures['supplier']=supplier
    ledger_rows=[]
    for sale in sales:
        wf=reader.resource('workflow-'+str(sale['id']),'/api/v1/sales-workflow/'+str(sale['id']),detail=True)
        captures['workflow-'+str(sale['id'])]=wf
        for shipment in (wf['rows'][0].get('data',{}).get('shipments',[]) if wf['rows'] else []):
            oid=shipment.get('outbound_id')
            if type(oid) is not int:return None,['OUTBOUND_ID_INVALID']
            ledger=reader.resource('ledger-'+str(oid),'/api/v1/stock/ledger',dict(resource='outbound-orders',record_id=oid))
            captures['ledger-'+str(oid)]=ledger;ledger_rows.extend(r for r in ledger['rows'] if r.get('sku')==entity['sku'])
    if opening_binding:
        opening=opening_binding.monitor.openingQuantity;policy=opening_binding.monitor.policy
    else:
        # Independently read whole SKU/warehouse ledger, not current stock + invented sales.
        full=reader.resource('ledger-scope-'+fingerprint([entity['sku'],entity['warehouseId']])[:20],'/api/v1/stock/ledger',dict(sku=entity['sku'],warehouse_name=entity['warehouseName']))
        if not full['complete'] or not ledger_rows or {r['id'] for r in full['rows']}!={r['id'] for r in ledger_rows}:return None,['OPENING_AND_LEDGER_COVERAGE_UNPROVEN']
        opening=str(sorted(ledger_rows,key=lambda r:(r['created_at'],r['id']))[0]['before_quantity']);policy=ForecastPolicy()
    scope=dict(tenantId='v2-rule-projection',storeIds=[entity['storeId']],warehouseIds=[entity['warehouseId']],canonicalSkuIds=[entity['sku']],fields=['quantity'])
    binding=SimpleNamespace(productId=entity['productId'],supplierId=str(q['supplier_id']),quoteId=str(q['id']),quoteNo=q['quote_no'],
        inventoryIds=tuple(entity['inventoryIds']),salesIds=tuple(str(s['id']) for s in sales),purchaseIds=(),openingQuantity=opening,policy=policy)
    mapping=SimpleNamespace(scope=scope,monitor=binding,sku=entity['sku'],sourceTenant=entity['sourceTenant'],sourceStore=entity['storeId'],sourceWarehouse=entity['warehouseId'],
        storeName=entity['storeName'],warehouseName=entity['warehouseName'],version='s01-v2-dynamic-v1')
    receipt=dict(completedAt=reader.state['startedAt'],acquisitionId='v2-'+fingerprint(entity)[:24])
    normalized=normalize_owned(captures,mapping,receipt,True)
    if normalized['input'] is None:return None,[i['code'] for i in normalized['issues'] if i['severity']=='BLOCK']
    snapshot=capture(project(AdmittedInput.model_validate(normalized['input']),'v2-'+entity['entityKey']))
    if not snapshot.calculation_allowed:return None,[i.code for i in snapshot.issues]
    return dict(supplyDemand=propose(snapshot),forecast=normalized['forecast'],input=normalized['input'],
        fieldProvenance=normalized['fieldProvenance'],snapshotId=snapshot.snapshotId,quality=[i.model_dump() for i in snapshot.issues]),[]


def analyze(catalog,entity,reader,*,opening_binding=None,requisition_authorized=None):
    if reader.state.get('decisionVersion')=='s01-product-demand-v1':
        from .decision import analyze_decision
        return analyze_decision(catalog,entity,reader,requisition_authorized=requisition_authorized)
    if reader.state.get('admissionVersion')=='s01-runtime-v1' and getattr(getattr(opening_binding,'monitor',None),'policy',None):
        from commerce_hub.data.projection.runtime import business_date
        catalog=dict(catalog,businessDate=business_date(reader.state['startedAt'],opening_binding.monitor.policy.timezone).isoformat())
    result=deepcopy(entity);c,q,p=constraints(catalog,entity)
    stock=[r for r in catalog['inventory']['rows'] if str(r['id']) in entity['inventoryIds']]
    result.update(analysisState='UNANALYZABLE',sourceGrade='UNAVAILABLE',quantity=None,sourceQuantity=None,
        unit=c['unit'],constraints=c,formalPurchases=formal_purchases(catalog,entity),
        inventory=dict(available=stock[0]['available'] if entity['identityVerified'] and len(stock)==1 and type(stock[0].get('available')) is int and stock[0]['available']>=0 else None,
            inventoryIds=entity['inventoryIds'],warehouseId=entity['warehouseId']),
        uncertainties=['NO_ATOMIC_CROSS_INTERFACE_SNAPSHOT','SELLABLE_ETA_UNKNOWN','FORMAL_PURCHASE_DEDUCTION_UNCONFIRMED'],
        riskGroup='UNVERIFIED',riskDate=None,sourceUrgency=None,ruleFailureCodes=[],ruleResult=None,sourceSuggestion=None,
        procurementEligibility=dict(eligible=False,hardBlocks=c['hardBlocks'][:],warnings=[],policyVersion='s01-v2-scheme-b-v1'),
        observedAt=reader.state['startedAt'])
    admission=None
    if reader.state.get('admissionVersion')=='s01-runtime-v1':
        from commerce_hub.data.sync.runtime import collect_runtime
        admission=collect_runtime(catalog,entity,reader,c,p,opening_binding=opening_binding)
        rules,failures=admission['ruleResult'],admission['ruleFailureCodes']
        # A baseline without purchase parameters is risk information. It must
        # not displace a separately valid ERP reference or become a PO quantity.
        if admission['riskOnly']:rules=None
    else:
        rules,failures=rule_result(catalog,entity,reader,opening_binding=opening_binding) if entity['identityVerified'] else (None,['IDENTITY_MAPPING_UNVERIFIED'])
    result['ruleFailureCodes']=failures
    if rules:
        supplied=rules['supplyDemand'];candidate=supplied['candidates'][0] if supplied['candidates'] else None
        result.update(sourceGrade='RULE_CALCULATED',analysisState='ANALYZED' if candidate else 'NO_REPLENISHMENT' if supplied['baseline'] and not supplied['baseline']['stockoutRisk'] and supplied['baseline']['gapQuantity']=='0' else 'NEEDS_REVIEW',
            quantity=integer(candidate['quantity']) if candidate else None,ruleResult=rules,riskGroup='RULE_CONFIRMED',
            riskDate=supplied['baseline']['firstShortageDate'] if supplied['baseline'] else None)
        if result['analysisState']=='NO_REPLENISHMENT':result['riskGroup']='NO_REPLENISHMENT'
    else:
        suggestions=[s for s in catalog['suggestions']['rows'] if str(s['id']) in entity['suggestionIds']]
        result['sourceSuggestionCount']=len(suggestions)
        result['sourceSuggestions']=[{k:s.get(k) for k in ['id','recommendation_no','sku','store_name','suggested_qty','status_text','created_at','updated_at']} for s in suggestions[:20]]
        if len(suggestions)==1 and catalog['suggestions']['complete']:
            s=suggestions[0];n=integer(s.get('suggested_qty'),zero=True)
            result['sourceSuggestion']={k:s.get(k) for k in ['id','recommendation_no','sku','store_name','suggested_qty','daily_sales','local_available','overseas_available','fba_available','inbound','urgency','stockout_date','status_text','generated_at','created_at','updated_at']}
            result.update(sourceGrade='REFERENCE_ONLY' if n is not None else 'UNVERIFIED',analysisState='ERP_REFERENCE' if n else 'NEEDS_REVIEW',
                quantity=n if n else None,sourceQuantity=n,sourceUrgency=s.get('urgency'),riskGroup='ERP_SOURCE',riskDate=s.get('stockout_date'))
            result['uncertainties']+=['ERP_ALGORITHM_UNKNOWN','ERP_DAILY_SALES_WINDOW_UNKNOWN','ERP_GENERATION_TIME_UNVERIFIED','ERP_PURCHASE_NETTING_UNKNOWN']
            if s.get('overseas_available') and s.get('overseas_available')==s.get('fba_available'):result['uncertainties'].append('OVERSEAS_FBA_BUCKETS_NOT_ADDED')
        elif suggestions:result.update(sourceGrade='UNVERIFIED',analysisState='NEEDS_REVIEW');result['uncertainties'].append('SUGGESTION_AMBIGUOUS_OR_QUERY_INCOMPLETE')
    hard=result['procurementEligibility']['hardBlocks']
    if admission and set(admission['inventoryBasis']['issues']) & {
        'STOCK_MOVEMENT_RECONCILIATION_FAILED','STOCK_EVENT_CHAIN_GAP','DUPLICATE_STOCK_EVENT',
        'FOREIGN_STOCK_EVENT','LEDGER_ARITHMETIC_MISMATCH','RESERVATION_OR_STOCK_SEMANTICS_UNCONFIRMED'}:
        hard.append('INVENTORY_BASIS_INCONSISTENT')
    if not result['quantity']:hard.append('NO_POSITIVE_RECOMMENDATION_BASIS')
    if any(not p['warehouseMatch'] for p in result['formalPurchases']):result['uncertainties'].append('RELATED_PURCHASE_TARGETS_DIFFERENT_WAREHOUSE')
    if result['sourceSuggestion'] and any(p.get('sourcePlanNumber')==result['sourceSuggestion']['recommendation_no'] and p['warehouseMatch'] for p in result['formalPurchases']):hard.append('KNOWN_FORMAL_PURCHASE_FOR_SOURCE_PLAN')
    # Source uncertainty is a warning, never an independent Scheme B prohibition.
    result['procurementEligibility']['hardBlocks']=sorted(set(hard))
    result['procurementEligibility']['warnings']=result['uncertainties'][:]
    result['procurementEligibility']['eligible']=not hard
    if admission is not None:
        from commerce_hub.data.quality.runtime import public_admission
        result.update(public_admission(admission,result,requisition_authorized=requisition_authorized))
        if result['analysisState']=='UNANALYZABLE' and result['sourceGrade']=='UNAVAILABLE' and result['capabilities']['reference']['enabled']:
            # A useful historical reference is a separate result, never a
            # current recommendation or an ERP suggestion with invented qty.
            result.update(analysisState='HISTORICAL_REFERENCE',sourceGrade='HISTORICAL_REFERENCE')
    return result


def priority(item):
    if item.get('decisionVersion')=='s01-product-demand-v1':
        d=item['decision'];rank=0 if d['stockoutRisk'] and d['status']=='REPLENISH' else 1 if d['status']=='REPLENISH' else 2 if d['status']=='NEEDS_REVIEW' else 3
        return rank,0,d.get('firstShortageDate') or '9999-12-31',item.get('sku',''),item['entityKey']
    group={'RULE_CONFIRMED':0,'ERP_SOURCE':1,'UNVERIFIED':2,'NO_REPLENISHMENT':3}.get(item.get('riskGroup'),2)
    urgency={'最急':0,'急':1,'一般':2}.get(item.get('sourceUrgency'),3) if group==1 else 0
    return group,urgency,item.get('riskDate') or '9999-12-31',item.get('sku',''),item['entityKey']


def statistics(values,version='v2-counts-v2'):
    values=list(values);states=[r.get('analysisState') for r in values]
    done=sum(s!='PENDING' for s in states)
    available=sum(s in {'ANALYZED','ERP_REFERENCE','NO_REPLENISHMENT','HISTORICAL_REFERENCE'} for s in states)
    result=dict(discoveredSkuCount=len({r['sku'] for r in values}) if version in {'v2-counts-v2','product-counts-v1'} else len({(r.get('productId'),r['sku']) for r in values}),scopeObjectCount=len(values),processedCount=done,
        ruleCalculated=sum(r.get('sourceGrade')=='RULE_CALCULATED' and r.get('analysisState')=='ANALYZED' for r in values),erpReference=states.count('ERP_REFERENCE'),
        noReplenishment=states.count('NO_REPLENISHMENT'),unanalyzable=states.count('UNANALYZABLE')+states.count('NEEDS_REVIEW'),failed=states.count('FAILED'),
        unfinished=states.count('PENDING'),coverage=available/len(values) if values else 0,processingCoverage=done/len(values) if values else 0,
        ruleSourceCount=sum(r.get('sourceGrade')=='RULE_CALCULATED' for r in values),erpSourceRecordCount=sum(r.get('sourceGrade')=='REFERENCE_ONLY' for r in values),modelCalls=0,businessMutations=0)
    if version in {'v2-counts-v2','product-counts-v1'}:result['productIdentityCount']=len({r['productId'] for r in values if r.get('productId')})
    if version=='product-counts-v1':
        from .products import decision_counts
        result.update(decision_counts(values))
    # Do not add a zero-valued field when validating older immutable reports.
    if 'HISTORICAL_REFERENCE' in states:result['historicalReference']=states.count('HISTORICAL_REFERENCE')
    return result
