"""D01 exact registered resources. No name/prefix membership or tenant-wide fallback."""
from copy import deepcopy
from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.projection.runtime import business_date
from commerce_hub.data.projection.purchases import FORMAL_STATES


def member_record(m):
    b=m.monitor
    return dict(sourceTenant=m.sourceTenant,storeId=m.sourceStore,warehouseId=m.sourceWarehouse,productId=b.productId,
        sku=m.sku,storeName=m.storeName,warehouseName=m.warehouseName,datasetId=b.datasetId,scopeVersion=b.scopeVersion,
        importBatchId=b.importBatchId,evidenceDigest=b.evidenceDigest,listingId=b.listingId,inventoryIds=list(b.inventoryIds),
        salesIds=list(b.salesIds),quoteId=b.quoteId,quoteNo=b.quoteNo)


def collect_registered(reader,tenant,mappings,entity=None):
    members=sorted([member_record(m) for m in mappings],key=lambda r:(r['sku'],r['storeId'],r['warehouseId']))
    if any(m['sourceTenant']!=tenant for m in members):raise ERPError('V2_SOURCE_TENANT_MISMATCH')
    if entity:
        members=[m for m in members if all(m[k]==entity[k] for k in ['sourceTenant','storeId','warehouseId','productId','sku'])]
        if len(members)!=1:raise ERPError('V2_BUSINESS_SCOPE_NOT_REGISTERED')
    monitoring=dict(mode='OWNED_REGISTERED',members=members,membershipDigest=fingerprint(members),
        salesCoverage='ALL_REGISTERED_SALES_IDS_NO_DATE_CUTOFF',unregisteredObjects='EXCLUDED')
    if reader.state.get('resources') and reader.state.get('monitoring')!=monitoring:raise ERPError('V2_REGISTERED_SCOPE_CHANGED')
    reader.state['monitoring']=monitoring;reader.checkpoint.save(reader.state)
    reader.authenticate(tenant)
    catalog={}
    def combine(parts):
        found={}
        for part in parts:
            for row in part['rows']:
                key=str(row['id'])
                if key in found and found[key]!=row:raise ERPError('ERP_DUPLICATE_RECORD')
                found[key]=row
        return dict(rows=list(found.values()),complete=all(p['complete'] for p in parts),total=len(found),
            errors=[p.get('error') for p in parts if not p['complete']])
    for name,resource,field in [('products','products','productId'),('stores','store-authorizations','storeId'),
        ('warehouses','warehouses','warehouseId'),('inventory','inventory','inventoryIds'),('listings','listings','listingId'),
        ('sales','sales-orders','salesIds')]:
        ids=sorted({str(v) for m in members for v in (m[field] if isinstance(m[field],list) else [m[field]])})
        parts=[]
        for offset in range(0,len(ids),50):
            selected=ids[offset:offset+50];query=dict(ids=','.join(selected))
            if name in {'sales','inventory'}:query['view']='full'
            cap=reader.resource(name+('-'+str(offset) if offset else ''),'/api/v1/'+resource,query)
            if any(str(r.get('tenant_id'))!=tenant or str(r['id']) not in selected for r in cap['rows']):raise ERPError('V2_REGISTERED_RESOURCE_MISMATCH')
            if cap['complete'] and {str(r['id']) for r in cap['rows']}!=set(selected):cap=dict(cap,complete=False,error='REGISTERED_RECORD_MISSING')
            parts.append(cap)
        catalog[name]=combine(parts)
    quotes=[];suggestions=[];formal=[]
    for i,m in enumerate(members):
        cap=reader.resource('quote-'+str(i),'/api/v1/supplier-quotes',dict(quote_no=m['quoteNo']))
        if any(str(q.get('product_id'))!=m['productId'] or q.get('sku')!=m['sku'] or str(q['id'])!=m['quoteId'] for q in cap['rows']):raise ERPError('V2_REGISTERED_RESOURCE_MISMATCH')
        quotes.append(cap)
        cap=reader.resource('suggestion-'+str(i),'/api/v1/replenishment',dict(field='sku',q=m['sku'],match='exact',store_name=m['storeName']))
        if any(str(r.get('tenant_id'))!=tenant or r.get('sku')!=m['sku'] or r.get('store_name')!=m['storeName'] for r in cap['rows']):raise ERPError('V2_REGISTERED_RESOURCE_MISMATCH')
        suggestions.append(cap)
    for i,warehouse in enumerate(sorted({m['warehouseName'] for m in members})):
        for j,status in enumerate(FORMAL_STATES):
            cap=reader.resource('formal-'+str(i)+'-'+str(j),'/api/v1/purchase-orders',dict(warehouse_name=warehouse,field='status_text',q=status,match='exact'))
            if any(str(r.get('tenant_id'))!=tenant or r.get('warehouse_name')!=warehouse or r.get('status_text')!=status for r in cap['rows']):raise ERPError('V2_FORMAL_STATE_FILTER_MISMATCH')
            formal.append(cap)
    catalog.update(quotes=combine(quotes),suggestions=combine(suggestions),formalPurchases=combine(formal),
        businessDate=business_date(reader.state['startedAt']).isoformat(),monitoring=monitoring,
        admissionVersion='s01-runtime-v1',timeBasis=dict(timezone='UTC+08:00',complete=True,startedAt=reader.state['startedAt'],completedAt=reader.receipt()['completedAt']))
    return catalog


def registered_entities(catalog,candidates):
    result=[]
    for m in catalog['monitoring']['members']:
        keys=['sourceTenant','storeId','warehouseId','productId','sku']
        matches=[e for e in candidates if all(e[k]==m[k] for k in keys)]
        if len(matches)==1:r=deepcopy(matches[0])
        else:
            r={k:m[k] for k in keys+['storeName','warehouseName']}
            r.update(entityKey=fingerprint([m['sourceTenant'],m['storeId'],m['warehouseId'],m['productId'],m['sku']]),
                name=m['sku'],identityVerified=False,identityIssues=['REGISTERED_RELATION_MISSING'],inventoryIds=[],suggestionIds=[])
        r['registeredMembership']={k:m[k] for k in ['datasetId','scopeVersion','importBatchId','evidenceDigest']}
        r['expectedInventoryIds']=m['inventoryIds']
        result.append(r)
    return result
