"""Task-local bounded scope reads; never infer complete history from window IDs."""
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.projection.monitor import ForecastPolicy
from commerce_hub.data.projection.runtime import evaluate_runtime


def collect_runtime(catalog,entity,reader,constraints,product,*,opening_binding=None):
    policy=getattr(getattr(opening_binding,'monitor',None),'policy',None) or ForecastPolicy()
    inv=dict(catalog['inventory'],rows=[r for r in catalog['inventory']['rows'] if str(r['id']) in entity['inventoryIds']])
    # Empty/unrealized-only catalogs without a registered baseline cannot prove
    # historical stock. Avoid one request per unrelated reference-only SKU.
    matching=[s for s in catalog['sales']['rows'] if s.get('store_name')==entity['storeName'] and s.get('shipping_warehouse')==entity['warehouseName']
        and any(l.get('sku')==entity['sku'] for l in s.get('item_list',[]))]
    bound=opening_binding is not None and hasattr(opening_binding.monitor,'openingQuantity')
    proof=dict(rows=[],complete=False,error='STOCK_CHECKPOINT_UNPROVEN')
    sales=matching;workflows={};scope_complete=False
    if entity['identityVerified'] and (bound or matching):
        # No date filter: stock conservation must retain events after a stable
        # baseline even after source orders leave the SMA window. Pagination,
        # total drift, request/record limits and authorization remain V2Reader's.
        name='sales-scope-'+fingerprint([entity['storeId'],entity['warehouseId']])[:20]
        history=reader.resource(name,'/api/v1/sales-orders',dict(view='full',store_name=entity['storeName'],shipping_warehouse=entity['warehouseName']))
        scope_complete=history['complete'] and not history.get('error')
        if any(str(s.get('tenant_id'))!=entity['sourceTenant'] or s.get('store_name')!=entity['storeName']
                or s.get('shipping_warehouse')!=entity['warehouseName'] for s in history['rows']):scope_complete=False
        sales=[s for s in history['rows'] if any(l.get('sku')==entity['sku'] for l in s.get('item_list',[]))]
        proof=reader.resource('stock-scope-'+fingerprint([entity['sku'],entity['warehouseId']])[:20],'/api/v1/stock/ledger',
            dict(sku=entity['sku'],warehouse_name=entity['warehouseName']))
        for s in sales:
            if s.get('payment_status')=='已支付' and s.get('fulfillment_status')=='已发货' and s.get('refund_status')=='无退款':
                wf=reader.resource('workflow-'+str(s['id']),'/api/v1/sales-workflow/'+str(s['id']),detail=True)
                if wf['complete'] and len(wf['rows'])==1:workflows[str(s['id'])]=wf['rows'][0].get('data',{})
    receipt=reader.receipt()
    receipt=dict(startedAt=receipt['startedAt'],completedAt=receipt['completedAt'],businessDate=catalog['businessDate'],
        scopeEvidence=fingerprint([entity['sourceTenant'],entity['productId'],entity['inventoryIds']]),
        inventoryProof=inv.get('bindingDigest'),salesProof=fingerprint(sales),movementProof=fingerprint(proof))
    result=evaluate_runtime(entity,product,inv,proof,sales,workflows,policy,receipt,constraints,
        opening_binding=opening_binding,scope_complete=scope_complete)
    result['demandWindow']['scopeCoverage']='COMPLETE_SCOPED_SOURCE' if scope_complete else 'UNPROVEN'
    result['inventoryBasis']['observedAt']=inv.get('observedAt')
    return result
