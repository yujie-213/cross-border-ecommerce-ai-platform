"""Business counting and SKU grouping. Never combine stock or demand across scopes."""
from collections import defaultdict


def decision_counts(values):
    rows=list(values)
    def selected(status):return [r for r in rows if r.get('decision',{}).get('status')==status]
    def skus(items):return len({r['sku'] for r in items})
    replenish=selected('REPLENISH');none=selected('NO_REPLENISHMENT')
    forecast=[r for r in rows if r.get('decision',{}).get('forecast',{}).get('available')]
    judged=replenish+none;risk=[r for r in rows if r.get('decision',{}).get('stockoutRisk')]
    differences=[r for r in rows if r.get('erpComparison',{}).get('significant')]
    unknown={r['sku'] for r in rows}-{r['sku'] for r in judged}
    return dict(analyzedSkuCount=skus(forecast),forecastScopeCount=len(forecast),judgedSkuCount=skus(judged),judgedScopeCount=len(judged),
        replenishSkuCount=skus(replenish),replenishScopeCount=len(replenish),
        noReplenishmentSkuCount=len({r['sku'] for r in none}-{r['sku'] for r in replenish}-{r['sku'] for r in rows if r.get('decision',{}).get('status') not in {'REPLENISH','NO_REPLENISHMENT'}}),
        noReplenishmentScopeCount=len(none),reviewSkuCount=len(unknown),reviewScopeCount=len(rows)-len(judged),
        riskSkuCount=skus(risk),riskScopeCount=len(risk),erpDifferenceSkuCount=skus(differences),erpDifferenceScopeCount=len(differences),
        forecastCoverage=skus(forecast)/skus(rows) if rows else 0,decisionCoverage=len(judged)/len(rows) if rows else 0)


def group_products(rows,priority):
    grouped=defaultdict(list)
    for r in rows:grouped[r['sku']].append(r)
    result=[]
    for sku,scopes in grouped.items():
        scopes.sort(key=priority);representative=dict(scopes[0]);counts=decision_counts(scopes)
        plans=[r['decision']['referenceReplenishmentQuantity'] for r in scopes if r.get('decision',{}).get('referenceReplenishmentQuantity') is not None]
        representative['productSummary']=dict(counts,scopeCount=len(scopes),storeCount=len({r['storeId'] for r in scopes if r.get('storeId')}),
            warehouseCount=len({r['warehouseId'] for r in scopes if r.get('warehouseId')}),referencePlanTotal=sum(plans) if plans else None,
            productIds=sorted({r['productId'] for r in scopes if r.get('productId')}),
            scopeKeys=[r['entityKey'] for r in scopes],totalMeaning='SUM_OF_INDEPENDENT_SCOPE_PLANS_NOT_POOLED_INVENTORY')
        result.append(representative)
    return sorted(result,key=priority)
