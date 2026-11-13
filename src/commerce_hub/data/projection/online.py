"""D02 online mapping and observed facts; no inferred demand or procurement rules."""
from commerce_hub.data.projection.observed import project_observations
from commerce_hub.data.sync.online import quantity
from commerce_hub.data.contracts import AdmittedInput, fingerprint
from datetime import datetime, timedelta

def observed(captures, mapping, receipt):
    def rows(name): return captures.get(name, {}).get('rows', [])
    required = ['inventory', 'product', 'store', 'warehouse', 'listing']
    exact = (all(captures.get(n, {}).get('complete') is True and rows(n) for n in required)
        and len(rows('product')) == len(rows('store')) == len(rows('warehouse')) == 1
        and all(str(r.get('tenant_id')) == mapping.sourceTenant for n in required for r in rows(n))
        and all(r.get('sku') == mapping.sku and str(r.get('wid')) == mapping.sourceWarehouse
            and str(r.get('store_id')) == mapping.sourceStore for r in rows('inventory'))
        and rows('product')[0].get('sku') == mapping.sku
        and str(rows('store')[0].get('id')) == mapping.sourceStore
        and str(rows('warehouse')[0].get('id')) == mapping.sourceWarehouse
        and all(r.get('sku') == mapping.sku and r.get('store_name') == mapping.storeName for r in rows('listing')))
    # A mismatched source response is never exposed as a trustworthy quantity.
    inventory = rows('inventory') if exact else []
    product = rows('product')[0] if exact else {}
    measures = [dict(field=f, value=quantity(r.get(k)), unit='SOURCE_PIECE')
        for r in inventory for f,k in [('physical','quantity'),('available','available')]][:20]
    domains = []
    for name, sources, measurements in [
        ('identity',required,[]), ('inventory',['inventory','buckets'],measures),
        ('demand',[n for n in captures if n.startswith('sales')],[]),
        ('supply',['purchases','purchase-draft'],[]), ('availability',['product','purchases'],[]),
        ('moq',['product','quotes'],[dict(field='moq',value=quantity(product.get('moq')),unit='SOURCE_PIECE')]),
        ('orderMultiple',['product'],[dict(field='carton_quantity',value=quantity(product.get('default_carton_qty')),unit='SOURCE_PIECE')]),
        ('quality',['quality'],[])]:
        sources = [s for s in sources if s in captures]
        state = ('ERROR' if any(captures[s].get('error') for s in sources) else
            'OBSERVED' if exact and name in {'identity','inventory','moq'} else 'INCOMPLETE')
        domains.append(dict(domain=name,state=state,measurements=measurements,
            sourceRefs=['read-'+captures[s]['fingerprint'] for s in sources if captures[s].get('fingerprint')][:20],
            sourceTimes=sorted({str(r['updated_at']) for s in sources for r in rows(s) if r.get('updated_at')})[:20]))
    projection = project_observations(dict(sourceSynthetic=mapping.sourceSynthetic,ownerConfirmed=True,
        revalidationFailed=not exact or any(c.get('error') for c in captures.values()), scope=mapping.scope,
        observedAt=receipt['completedAt'],domains=domains))
    return projection.model_dump(mode='json'), bool(exact)


def normalize_online(captures, mapping, receipt, mapping_verified):
    """Normalize current source facts only; unknown enterprise semantics stay blocked.

    The sole pre-existing teaching policy is an explicit seven-order replay. It
    cannot be applied to arbitrary SKUs or repaired with fixed catalog values.
    """
    issues=[]
    def block(code,path,category='SOURCE_DATA'):
        issues.append(dict(code=code,severity='BLOCK',path=path,affects='CALCULATION',category=category))
    for name,cap in captures.items():
        if cap.get('error'):block(cap['error'],name,'TECHNICAL')
        elif cap.get('complete') is not True:block('SOURCE_COVERAGE_INCOMPLETE',name,'TECHNICAL')
    if not mapping_verified:block('IDENTITY_MAPPING_UNVERIFIED','mapping','SOURCE_DATA')
    if not mapping.teachingReplay:
        for code,path in [('NET_AVAILABLE_UNCONFIRMED','inventory'),('DEMAND_RULE_UNCONFIRMED','demand'),
            ('SUPPLY_COVERAGE_UNPROVEN','supply'),('AVAILABLE_DATES_UNCONFIRMED','supply'),
            ('INDEPENDENT_ORDER_MULTIPLE_UNKNOWN','policy'),('QUALITY_STATE_UNKNOWN','quality')]:
            block(code,path,'BUSINESS_RULE')
        return dict(input=None,issues=issues,ruleVersion=None,assumptions=[])
    assumptions=['TEACHING_RULES_ONLY','NET_AVAILABLE_BY_TEACHING_RULE_NO_SECOND_RESERVATION_DEDUCTION',
        'SEVEN_EXACT_20261101_07_SALES_REPLAYED_D1_D7_NOT_ENTERPRISE_FORECAST',
        'EXACT_TEACHING_A_SUPPLY_COLLECTION_ONLY','MULTIPLE_6_IS_CONTROLLED_RULE_NOT_CARTON_INFERENCE',
        'CANDIDATE_D7_IS_TEACHING_ASSUMPTION_NOT_ERP_ETA','NO_ENTERPRISE_BUSINESS_ADMISSION']
    def rows(name):return captures.get(name,{}).get('rows',[])
    inventory=rows('inventory');product=rows('product');quality=rows('quality');drafts=rows('purchase-draft')
    if len(inventory)!=1:block('AMBIGUOUS_OR_MISSING_INVENTORY','inventory')
    if len(product)!=1 or product[0].get('sku')!=mapping.sku or product[0].get('product_type')!='TEACHING_SIMULATION':
        block('TEACHING_PRODUCT_IDENTITY_UNPROVEN','product')
    if captures.get('purchases',{}).get('complete') is not True or rows('purchases'):
        block('TEACHING_A_EMPTY_SUPPLY_NOT_PROVEN','supply')
    # A created draft is never silently treated as an effective/open supply.
    if len(drafts)!=1 or drafts[0].get('status_text') not in {'DRAFT','未提交','草稿'}:
        block('PURCHASE_DRAFT_STATUS_UNCONFIRMED','supply')
    demands=[];source_ids=set()
    anchor=datetime.fromisoformat(receipt['completedAt'])
    for day in range(1,8):
        values=rows(f'sales-{day}')
        if len(values)!=1:
            block('DEMAND_WINDOW_INCOMPLETE',f'sales-{day}');continue
        row=values[0];items=row.get('item_list')
        expected_order='S01-AI-TEST-20261112'+f'-SALE-202611{day:02d}'
        if (row.get('order_sn')!=expected_order or str(row.get('tenant_id'))!=mapping.sourceTenant
            or row.get('store_name')!=mapping.storeName or row.get('shipping_warehouse')!=mapping.warehouseName
            or not str(row.get('order_time','')).startswith(f'2026-11-{day:02d} ')
            or not isinstance(items,list) or len(items)!=1 or items[0].get('sku')!=mapping.sku
            or row.get('id') is None or row['id'] in source_ids or quantity(items[0].get('quantity')) is None):
            block('DEMAND_SCOPE_OR_DATE_UNVERIFIED',f'sales-{day}');continue
        source_ids.add(row['id'])
        demands.append(dict(recordId='online-sale-'+fingerprint([row['id'],expected_order])[:24],
            sku=mapping.scope['canonicalSkuIds'][0],store=mapping.scope['storeIds'][0],warehouse=mapping.scope['warehouseIds'][0],
            unit='EA',day=(anchor.date()+timedelta(days=day)).isoformat(),quantity=quantity(items[0]['quantity']),
            semantics='INCREMENTAL_EXCLUDES_RESERVED'))
    disposition='UNKNOWN'
    if (len(quality)==1 and quality[0].get('order_sn')=='S01-AI-TEST-20261112-QC-A'
        and str(quality[0].get('tenant_id'))==mapping.sourceTenant and quality[0].get('warehouse_name')==mapping.warehouseName
        and any(x.get('sku')==mapping.sku for x in quality[0].get('item_list',[]))):
        disposition={'TEACHING_QUALITY_CLEAR':'VERIFIED_CLEAR','TEACHING_QUALITY_INVESTIGATE':'INVESTIGATE'}.get(quality[0].get('qc_status'),'UNKNOWN')
    if issues:return dict(input=None,issues=issues,ruleVersion='teaching-s01-rules-v1',assumptions=assumptions)
    row=inventory[0];p=product[0]
    try:
        canonical=dict(sku=mapping.scope['canonicalSkuIds'][0],store=mapping.scope['storeIds'][0],warehouse=mapping.scope['warehouseIds'][0])
        input=AdmittedInput(sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',
            fixtureId='online-'+receipt['acquisitionId'],provenanceRef='online-source-'+fingerprint(receipt)[:32],
            rulesRef='teaching-s01-rules-v1',asOf=anchor,coverageComplete=True,
            mapping=dict(version=mapping.version,sourceSku=canonical['sku'],sourceStore=canonical['store'],
                sourceWarehouse=canonical['warehouse'],canonicalSkuId=canonical['sku'],storeId=canonical['store'],
                warehouseId=canonical['warehouse'],sourceUnit='EA',unit='EA',unitsPerSourceUnit='1'),
            inventory=[dict(recordId='online-inventory-'+fingerprint(row['id'])[:24],**canonical,unit='EA',
                availableQty=quantity(row.get('available')),reservedQty=None,semantics='NET_AVAILABLE',sourceUpdatedAt=row['updated_at'])],
            demand=demands,supply=[],policy=dict(version='teaching-s01-rules-v1',horizonDays=7,bufferDays=0,maxAgeHours=24,
                moq=quantity(p.get('moq')),orderMultiple='6',candidateDates=[(anchor.date()+timedelta(days=7)).isoformat()],
                maxOrderQty='120',otherConstraints='REVIEWED_NOT_APPLICABLE',qualityDisposition=disposition))
        return dict(input=input.model_dump(mode='json'),issues=[],ruleVersion='teaching-s01-rules-v1',assumptions=assumptions)
    except (ValueError,KeyError,TypeError):
        block('SOURCE_INPUT_FIELDS_INVALID','input')
        return dict(input=None,issues=issues,ruleVersion='teaching-s01-rules-v1',assumptions=assumptions)
