"""One shared read per resource/page, not one full online Agent per SKU."""
from datetime import datetime,timedelta,timezone
from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.projection.purchases import FORMAL_STATES


def collect_catalog(reader,tenant,entity=None):
    reader.authenticate(tenant)
    anchor=datetime.fromisoformat(reader.state['startedAt'])
    day=anchor.astimezone(timezone(timedelta(hours=8))).date()
    resources=[('stores','store-authorizations',{}),('warehouses','warehouses',{}),('products','products',{}),
        ('inventory','inventory',dict(view='full')),('suggestions','replenishment',{}),('quotes','supplier-quotes',{}),
        ('listings','listings',{}),('sales','sales-orders',dict(view='full',date_from=(day-timedelta(days=7)).isoformat(),date_to=day.isoformat()))]
    if entity:
        exact=dict(field='sku',q=entity['sku'],match='exact')
        filters=dict(stores=dict(ids=entity['storeId']),warehouses={},products=exact,
            inventory=dict(exact,store_id=entity['storeId']),suggestions=dict(exact,store_name=entity['storeName']),
            quotes=dict(sku=entity['sku']),listings=dict(exact,store_name=entity['storeName']),
            sales=dict(store_name=entity['storeName'],shipping_warehouse=entity['warehouseName']))
        resources=[(n,r,dict(p,**filters[n])) for n,r,p in resources]
    catalog={}
    for name,resource,params in resources:
        catalog[name]=reader.resource(name,'/api/v1/'+resource,params)
        if name!='quotes' and any(str(r.get('tenant_id'))!=str(tenant) for r in catalog[name]['rows']):
            raise ERPError('V2_SOURCE_TENANT_MISMATCH')
    parts=[]
    for i,state in enumerate(FORMAL_STATES):
        part=reader.resource('formal-'+str(i),'/api/v1/purchase-orders',dict(field='status_text',q=state,match='exact'))
        if any(str(r.get('tenant_id'))!=str(tenant) or r.get('status_text')!=state for r in part['rows']):raise ERPError('V2_FORMAL_STATE_FILTER_MISMATCH')
        parts.append(part)
    rows=[r for p in parts for r in p['rows']]
    if len({r['id'] for r in rows})!=len(rows):raise ERPError('ERP_DUPLICATE_RECORD')
    catalog['formalPurchases']=dict(rows=rows,complete=all(p['complete'] for p in parts),total=len(rows),
        errors=[p['error'] for p in parts if p.get('error')])
    catalog['businessDate']=day.isoformat()
    return catalog
