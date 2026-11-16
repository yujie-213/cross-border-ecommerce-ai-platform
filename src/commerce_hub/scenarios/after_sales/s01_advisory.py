"""Display assembly only. Caller already authorized S01 identities; never mutate inputs."""
from copy import deepcopy
from .risk import QualityRiskReadPort
from .common import now


def attach(domain,actor,rows,history=None):
    values=[deepcopy(r) for r in rows]
    port=QualityRiskReadPort(domain)
    for start in range(0,len(values),100):
        chunk=values[start:start+100]
        identities=[{k:r.get(k) for k in ('sourceTenant','productId','sku','storeId','warehouseId')} for r in chunk]
        results=port.lookup(actor,identities) if domain is not None else [dict(identity=i,status='UNVERIFIED',checkedAt=now(),riskRefs=[],reason='售后风险能力未启用') for i in identities]
        for r,result in zip(chunk,results):
            r['qualityRiskAdvisory']=result
            if history is not None:
                r['qualityRiskHistory']=next((h for h in history if h['identity']==result['identity']),None)
    return values
