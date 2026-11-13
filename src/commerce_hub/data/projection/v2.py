"""Dynamic source identity, with unresolved objects retained rather than silently dropped."""
from collections import defaultdict
from commerce_hub.data.contracts import fingerprint


def entities(catalog,tenant):
    products=catalog.get('products',{}).get('rows',[])
    stores=catalog.get('stores',{}).get('rows',[])
    warehouses=catalog.get('warehouses',{}).get('rows',[])
    inventory=catalog.get('inventory',{}).get('rows',[])
    suggestions=catalog.get('suggestions',{}).get('rows',[])
    by_id={str(p['id']):p for p in products};by_sku=defaultdict(list)
    for p in products:by_sku[p.get('sku')].append(p)
    store_ids={str(r['id']):r for r in stores};warehouse_ids={str(r['id']):r for r in warehouses}
    store_names=defaultdict(list)
    for s in stores:store_names[s.get('store_name')].append(s)
    found={};seen_products=set()
    def add(sku,pid,sid,wid,issues=()):
        identity=[str(tenant),str(sid or ''),str(wid or ''),str(pid or ''),sku]
        key=fingerprint(identity)
        if key not in found:
            p=by_id.get(str(pid),{});s=store_ids.get(str(sid),{});w=warehouse_ids.get(str(wid),{})
            found[key]=dict(entityKey=key,sourceTenant=str(tenant),storeId=str(sid) if sid else None,
                warehouseId=str(wid) if wid else None,productId=str(pid) if pid else None,sku=sku or 'UNKNOWN',
                name=p.get('name') or sku or '未确认商品',storeName=s.get('store_name'),warehouseName=w.get('name'),
                identityIssues=list(issues),scopeEvidence='ERP_PRODUCT_INVENTORY_IDS' if not issues else 'UNRESOLVED',
                inventoryIds=[],suggestionIds=[],unit=p.get('unit'),productSourceUpdatedAt=p.get('updated_at'))
        else:found[key]['identityIssues']=sorted(set(found[key]['identityIssues'])|set(issues))
        if pid:seen_products.add((str(pid),sku))
        return found[key]
    for inv in inventory:
        pid,sid,wid=map(lambda v:str(v) if v is not None else None,[inv.get('product_id'),inv.get('store_id'),inv.get('wid')])
        issues=[];p=by_id.get(pid);s=store_ids.get(sid);w=warehouse_ids.get(wid)
        if p is None or p.get('sku')!=inv.get('sku') or len(by_sku.get(inv.get('sku'),[]))!=1:issues.append('PRODUCT_IDENTITY_AMBIGUOUS')
        if s is None or s.get('store_name')!=inv.get('store_name'):issues.append('STORE_IDENTITY_AMBIGUOUS')
        if w is None or w.get('name')!=inv.get('warehouse_name'):issues.append('WAREHOUSE_IDENTITY_AMBIGUOUS')
        e=add(inv.get('sku'),pid,sid,wid,issues);e['inventoryIds'].append(str(inv['id']))
    for suggestion in suggestions:
        sku=suggestion.get('sku');ps=by_sku.get(sku,[]);ss=store_names.get(suggestion.get('store_name'),[])
        matching=[e for e in found.values() if e['sku']==sku and len(ss)==1 and e['storeId']==str(ss[0]['id'])]
        # Saved suggestions have no warehouse FK. Never apply one source record to multiple warehouses.
        if len(matching)==1 and len(ps)==1:
            matching[0]['suggestionIds'].append(str(suggestion['id']))
        else:
            e=add(sku,ps[0]['id'] if len(ps)==1 else None,ss[0]['id'] if len(ss)==1 else None,None,['SUGGESTION_WAREHOUSE_OR_PRODUCT_UNRESOLVED'])
            e['suggestionIds'].append(str(suggestion['id']))
    for product in products:
        if (str(product['id']),product.get('sku')) not in seen_products:add(product.get('sku'),product['id'],None,None,['NO_UNIQUE_STORE_WAREHOUSE_RELATION'])
    for e in found.values():
        e['identityVerified']=not e['identityIssues'] and bool(e['inventoryIds'])
        for name in ['products','stores','warehouses','inventory']:
            if not catalog.get(name,{}).get('complete'):
                e['identityVerified']=False;e['identityIssues'].append('IDENTITY_ENUMERATION_INCOMPLETE:'+name)
    return sorted(found.values(),key=lambda e:e['entityKey'])
