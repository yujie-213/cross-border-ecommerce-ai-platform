"""Public QualityRiskReadPort v1. No S01 algorithm or procurement dependency."""
from datetime import datetime,timezone
from sqlalchemy import select
from commerce_hub.governance.access.service import AccessDenied
from .common import WORKSPACE,now,timestamp,require,digest
from .tables import assets


def matches(risk_identity,identity):
    return all(str(risk_identity[k])==str(identity.get(k,'')) for k in ('sourceTenant','productId','sku','storeId')) and (
        risk_identity['warehouseMode']=='ALL_STORE_WAREHOUSES' or str(identity.get('warehouseId')) in risk_identity['warehouseIds'])


class QualityRiskReadPort:
    version='1.0.0'

    def __init__(self,domain):self.domain=domain

    def historical(self,principal,snapshots):
        """Saved versions are history, disclosed only while their B scope is readable."""
        results=[]
        for start in range(0,len(snapshots),100):
            chunk=snapshots[start:start+100]
            current=self.lookup(principal,[s['identity'] for s in chunk])
            for saved,latest in zip(chunk,current):
                refs=[]
                if latest['status'] in {'MATCHED','NONE'}:
                    for ref in saved['riskRefs']:
                        try:
                            risk=self.domain.store.read(principal,'RISK',ref['riskId'],ref['version'])
                            if risk['body']['_state']=='CONFIRMED':refs.append(ref)
                        except Exception:pass
                results.append(dict(identity=saved['identity'],checkedAt=saved['checkedAt'],riskRefs=refs,
                    status='HISTORICAL' if latest['status'] in {'MATCHED','NONE'} else 'UNVERIFIED',reason='历史引用不代表当前有效'))
        return results

    def lookup(self,principal,identities,*,as_of=None):
        require(isinstance(identities,list) and len(identities)<=100,'RISK_LOOKUP_LIMIT')
        checked=as_of or now();stamp=timestamp(checked)
        unavailable=[dict(identity=i,status='UNVERIFIED',checkedAt=checked,riskRefs=[],reason='风险未核实') for i in identities]
        if not self.domain.tasks.after_sales_enabled:return unavailable
        try:
            store=self.domain.store
            with store.engine.begin() as conn:
                store.access._assert_current(conn,principal,lock=True)
                rows=conn.execute(select(assets).filter_by(tenant_id=principal.tenant_id,workspace=WORKSPACE).where(assets.c.kind=='RISK')).mappings().all()
                risks=rows
                results=[]
                for identity in identities:
                    refs=[];visible=False
                    for risk in risks:
                        if not store.source_visible(conn,risk):continue
                        try:store.authorize(conn,principal,'b:risk:consume',risk['scope'])
                        except AccessDenied:continue
                        b=risk['body'];candidate=identity
                        if not matches(b['identity'],candidate):continue
                        visible=True
                        if risk['state']=='CONFIRMED' and timestamp(b['validFrom'])<=stamp<timestamp(b['validUntil']):
                            refs.append(dict(riskId=risk['id'],version=risk['revision'],reason=b['reason'],limitations=b['limitations'],
                                sourceNature=risk['scope']['sourceNature'],validUntil=b['validUntil'],investigationId=b['investigationId'],confirmedBy=b['confirmedBy']))
                    # No access to the ERP risk scope never implies no risks.
                    results.append(dict(identity=identity,status='MATCHED' if refs else 'NONE' if visible else 'UNVERIFIED',checkedAt=checked,riskRefs=refs,
                        reason='仅提醒，原补货与采购规则继续适用' if refs else '当前范围未发现适用的已确认风险' if visible else '未配置适用风险范围'))
                return results
        except Exception:return unavailable
