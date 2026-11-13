"""D02 online mapping and observed facts; no inferred demand or procurement rules."""
from commerce_hub.data.projection.observed import project_observations
from commerce_hub.data.sync.online import quantity

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
