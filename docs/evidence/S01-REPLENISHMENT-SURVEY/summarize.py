"""Offline whitelist projection of private survey responses; never performs network IO."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
PRIVATE=ROOT/'data/private/s01-replenishment-survey'
OUT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def pin(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def pick(row,keys):return {k:row.get(k) for k in keys}


def main():
    original_path=sorted(PRIVATE.glob('*/findings.json'))[-1]
    supplement_path=sorted(PRIVATE.glob('*/supplement.json'))[-1]
    trace_path=sorted(PRIVATE.glob('*/purchase-traces.json'))[-1]
    original,supplement,traces=map(load,[original_path,supplement_path,trace_path])
    events=[e for p in sorted(PRIVATE.glob('*/journal.json')) for e in load(p)['events']]
    assert len(events)<=80 and all(e.get('httpStatus')==200 for e in events)
    for e in events:
        if e.get('privateResponse'):
            p=(ROOT/e['privateResponse']).resolve()
            assert p.is_relative_to(PRIVATE.resolve())
            assert hashlib.sha256(p.read_bytes()).hexdigest()==e['sha256']
    assert all(e['method']=='GET' or e['method']=='POST' and e['path'] in {
        '/api/auth-server/oauth/access-token','/erp/sc/routing/restocking/analysis/getSummaryList'} for e in events)
    expected={
        'YF-SO-NG-OS': [120,5,0,0,0,0,'最急','2026-11-14','待确认'],
        'YF-SO-PZ-L': [1200,60,0,0,0,0,'最急','2026-11-14','待确认'],
        'YF-SO-QD-S': [60,10,0,40,40,200,'急','2026-12-08','已生成采购单'],
        'YF-SO-QD-L': [50,1,0,60,60,0,'一般','2027-01-13','待确认'],
        'YF-SO-PZ-M': [0,6,0,0,0,0,'最急','2026-11-14','待确认']}
    fields=['suggested_qty','daily_sales','local_available','overseas_available','fba_available','inbound','urgency','stockout_date','status_text']
    comparisons=[]
    for item in original['skus']:
        sku=item['sku'];r=item['replenishment']['rows'][0]
        assert item['replenishment']['complete'] and item['replenishment']['total']==1
        assert [r.get(k) for k in fields]==expected[sku]
        assert len(item['product']['rows'])==len(item['inventory']['rows'])==1
        product,stock=item['product']['rows'][0],item['inventory']['rows'][0]
        assert stock['product_id']==product['id'] and stock['sku']==r['sku'] and stock['store_id']==original['store']['id']
        assert stock['available']==r['fba_available'] and stock['quantity']==stock['available']
        assert item['details']==[[200,r]] and item['contexts'][0][1]['record']==r
        comparisons.append(dict(sku=sku,sourceClass='REAL_NETWORK_OBSERVATION_OF_EXISTING_TEACHING_RECORD',
            tenantId=r['tenant_id'],storeId=original['store']['id'],storeName=r['store_name'],
            recommendationId=r['id'],recommendationNumber=r['recommendation_no'],
            screenshotObserved=dict(zip(fields,expected[sku])),restObserved=pick(r,fields),pageApiMatch=True,
            timestamps=pick(r,['generated_at','created_at','updated_at']),
            generatedAtEqualsStockoutDate=r['generated_at']==r['stockout_date'],
            product=pick(product,['id','sku','unit','moq','default_carton_qty','procurement_lead_days']),
            supplierConfigured=bool(product.get('supplier_name')),
            inventory=pick(stock,['id','tenant_id','store_id','wid','product_id','sku','quantity','available']),
            listingCount=item['listing'].get('total'),listingComplete=item['listing']['complete'],
            unitEvidence='PRODUCT_UNIT_PIECE_VERIFIED;SUGGESTION_FIELD_UNIT_METADATA_NOT_EXPLICIT',
            suggestionInterpretation='SAVED_SOURCE_SUGGESTION_NOT_DETERMINISTIC_NEED',
            projectOwnedMember=False,classification='REFERENCE_ONLY',procurementAllowed=False))
    purchases=[]
    for item in supplement['purchases']:
        for st,po in item['details']:
            assert st==200 and po in item['batch']['rows']
            t=next(t for t in traces if t['purchaseId']==po['id'])
            approvals=[pick(a,['id','tenant_id','business_type','business_no','status_text','submitted_at','decided_at']) for code,a in t['approvals'] if code==200]
            assert approvals and all(a['tenant_id']==po['tenant_id'] and a['business_no']==po['order_sn'] for a in approvals)
            deliveries=[pick(r['record'],['id','tenant_id','purchase_order_sn','warehouse_name','status_text','received_qty','item_list'])
                for r in t['context']['related'] if r['resource']=='supplier-deliveries']
            purchases.append(dict(sku=item['sku'],purchase=pick(po,['id','tenant_id','order_sn','warehouse_name','status_text','planned_arrival','received_qty','pending_qty','source_plan_no','created_at','updated_at']),
                lines=[pick(x,['sku','quantity']) for x in po['item_list']],independentDetailMatches=True,
                approvals=approvals,deliveryContext=deliveries,
                relation='EXPLICIT_SOURCE_PLAN' if po['source_plan_no'] else 'SAME_SKU_ONLY_NO_EXPLICIT_SOURCE_PLAN',
                qualifiesForCurrentP3OwnedScope=False,eligibleSupplyQuantity=None))
    b=supplement['batchRest']
    assert b['complete'] and b['total']==5 and b['pages']==3
    assert all(r['unchanged'] for r in supplement['repeatedRecommendations'])
    current=dict(result='REFERENCE_ONLY',restClassification='REFERENCE_ONLY',compatSelectedClassification='UNVERIFIED',
        reportRef='docs/reports/S01_ERP补货建议来源验证与V2可行性_20261113.md',
        observedAt=datetime.now(timezone.utc).isoformat(),applicationCommit='60e9cf2d53d368999936b894fa8c7f6d32352d9d',
        scope=dict(tenantId=1,storeId=1,storeName='MIMI Apparel US',role='administrator',broadPermissionsObserved=True,
            accountNamePublished=False,explicitlyAuthorizedSurveySKUs=list(expected),projectOwnedMembershipGranted=False,
            independentInventoryWarehouseIds=[303],sourceRecommendationWarehouseId='NOT_PRESENT',
            incidentalCompatStoreRows=2,incidentalRowsAnalyzedAsMembers=False,wholeStoreDiscoveryComplete=False),
        counts=dict(targetRecommendationRecords=5,positiveQuantityRecords=4,zeroQuantityRecords=1,usableFallbackRecords=0,
            httpAttempts=len(events),httpStatus=dict(Counter(str(e['httpStatus']) for e in events)),
            methodCounts=dict(Counter(e['method'] for e in events)),authenticationRequests=3,readOnlyQueryPosts=3,
            businessReads=60,businessMutations=0,modelRequests=0),
        latencyMs=dict(min=min(e['elapsedMs'] for e in events),max=max(e['elapsedMs'] for e in events),total=sum(e['elapsedMs'] for e in events)),
        comparisons=comparisons,relatedPurchases=purchases,
        pagination=dict(restSelectedIds=dict(total=5,pages=3,pageSize=2,complete=True,offsets=[0,2,4],duplicateRows=0),
            compatSelectedMSKU=dict(total=original['compatBatch']['total'],complete=original['compatBatch']['complete']),
            compatStoreMSKU=dict(total=supplement['compatStoreMSKU']['total'],fetched=len(supplement['compatStoreMSKU']['rows']),
                complete=False,reason='INTENTIONAL_BOUNDED_PAGE_LIMIT_NO_TRAVERSAL'),
            compatStoreASIN=dict(total=supplement['compatStoreASIN']['total'],complete=supplement['compatStoreASIN']['complete'])),
        verified=['5_TARGET_PAGE_REST_VALUES_MATCH','PRODUCT_AND_INVENTORY_TENANT_STORE_SKU_IDS_MATCH',
            'PRODUCT_UNIT_PIECE','REST_BATCH_3_PAGE_COMPLETE','QUERY_POST_READONLY_CATALOG_AND_LOCAL_SCHEMA',
            'QD_S_PO_200_REMAINING_AND_APPROVAL_PASSED','PZ_M_EXPLICIT_SOURCE_PO_150_APPROVAL_PENDING',
            'FIVE_RECORDS_UNCHANGED_ON_REPEAT_GET'],
        unknown=['SUGGESTION_ALGORITHM_AND_VERSION','DAILY_SALES_DENOMINATOR_WINDOW','SUGGESTION_UNIT_METADATA_CONVERSION',
            'TRUE_GENERATION_TIME_AND_SLA','REALTIME_OR_PERIODIC_RECALCULATION','APPROVED_PO_DEDUCTION',
            'TRANSIT_ETA_AND_PARTIAL_RECEIPT_DEDUCTION','RECOMMENDATION_WAREHOUSE_BINDING',
            'QD_S_EXPLICIT_RECOMMENDATION_TO_PO_LINK','PZ_M_ZERO_REASON_CODE_OR_CALCULATION_FAILURE_TRACE',
            'COMPAT_QUANTITY_SUG_PURCHASE_NONEMPTY_TARGET_MAPPING'],
        exceptions=dict(currentHTTPFailures=[],currentIncompleteResponse='compat store MSKU read deliberately capped at 2/667; not a complete batch',
            retainedHistorical503Evidence='docs/evidence/S01-FORECAST-SURVEY/verification.json'),
        traceEvents=[{k:v for k,v in e.items() if k in ['method','path','parameters','label','attempt','at','httpStatus','elapsedMs','sha256','privateResponse','errorType']} for e in events],
        privateArtifactPins=[pin(p) for p in [original_path,supplement_path,trace_path,*sorted(PRIVATE.glob('*/journal.json'))]],
        assumptions=['Product unit piece suggests source quantity uses piece, but field-specific unit contract is not proven',
            'No Listing and empty MSKU query may explain missing compat matches; causal implementation not proven',
            'Teaching product descriptions are author-maintained scenario intent, not calculator logs or instructions'],
        decision='REFERENCE DISPLAY ONLY; NO_DIRECT_REQUISITION; V2_DESIGN_RECOMMENDED_PENDING_SCOPE_AND_SOURCE_CONTRACT_APPROVAL')
    (OUT/'summary.json').write_text(json.dumps(current,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(result=current['result'],records=5,positive=4,zero=1,usableFallback=0,httpAttempts=len(events))))


if __name__=='__main__':main()
