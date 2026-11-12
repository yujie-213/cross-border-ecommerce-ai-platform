"""OFFLINE observed-contract fixture; never actual ERP or business-admission evidence."""
from commerce_hub.data.projection.observed import project_observations

def observed_fixture(scope=None):
    scope=scope or dict(tenantId="teaching-fixture",storeIds=["store-fixture"],warehouseIds=["warehouse-fixture"],canonicalSkuIds=["sku-fixture"],fields=["quantity"])
    domains=[dict(domain=name,state="OBSERVED" if name in {"identity","inventory"} else "MISSING",sourceRefs=["read-"+"a"*64])
        for name in ["identity","inventory","demand","supply","availability","moq","orderMultiple","quality"]]
    domains[1]["measurements"]=[dict(field="available",value="96",unit="SOURCE_PIECE")]
    domains[1]["sourceTimes"]=["2026-09-16 23:00:00"]
    return project_observations(dict(sourceSynthetic=True,ownerConfirmed=True,scope=scope,observedAt="2026-11-12T00:00:00Z",domains=domains)).model_dump(mode="json")
