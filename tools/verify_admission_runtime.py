"""Explicit read-only historical replay/live validation for runtime admission.

Requires a private source checkout for original owned mappings and captures.
Only a whitelisted summary is public; credentials, original records and HTTP
responses remain in ignored private directories. No ERP business writes/models.
"""
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
from types import SimpleNamespace
from commerce_hub.data.sync.online import OnlineMapping
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.projection.runtime import evaluate_runtime
from commerce_hub.scenarios.s01_v2.analysis import constraints,analyze

ROOT=Path(__file__).resolve().parents[1]


def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((json.dumps(v,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--live',action='store_true');args=p.parse_args()
    source=args.source_root.resolve();maps=[OnlineMapping.model_validate(m) for m in read(source/'data/private/s01-mvp-20261113/mapping-proposed.json')]
    if len(maps)!=2 or {m.sku for m in maps}!={'HL-CBL100-2M','HL-MUG350-WH'}:raise ValueError('EXACT_OWNED_MAPPING_REQUIRED')
    folders=['verification-HL-CBL100-2M-096bec03','verification-HL-MUG350-WH-7d5b061e']
    summary=dict(nature='ORIGINAL_ERP_FACTS_OFFLINE_REPLAY_EXPLICIT_ASOF',businessWrites=0,models=0,targets=[])
    for m,folder in zip(maps,folders):
        path=source/'data/private/s01-mvp-20261113'/folder;caps=read(path/'captures.json')
        digests={f:hashlib.sha256((path/f).read_bytes()).hexdigest() for f in ('captures.json','receipt.json','asset.json')}
        assert all(v['fingerprint']==fingerprint(v['rows']) for v in caps.values())
        e=dict(entityKey='history-'+fingerprint(m.scope)[:24],identityVerified=True,sourceTenant=m.sourceTenant,productId=m.monitor.productId,
            storeId=m.sourceStore,warehouseId=m.sourceWarehouse,sku=m.sku,storeName=m.storeName,warehouseName=m.warehouseName,inventoryIds=list(m.monitor.inventoryIds),suggestionIds=[])
        records=[]
        for day in ['2026-11-13','2026-11-14']:
            when=day+'T06:20:30+00:00';inv=deepcopy(caps['inventory']);inv['observedAt']=when
            catalog=dict(products=caps['product'],quotes=caps['quotes'],inventory=inv,formalPurchases=dict(rows=[],complete=True),businessDate=day)
            # Historical quote has no currency in some captures: exact old
            # source quote remains unchanged. Use confirmed USD from registered
            # source package for the isolated original-value regression only.
            catalog['quotes']=deepcopy(catalog['quotes'])
            for q in catalog['quotes']['rows']:q.setdefault('currency','USD')
            c,_,product=constraints(catalog,e)
            ledger=[r for k,v in caps.items() if k.startswith('ledger-') for r in v['rows'] if r.get('sku')==m.sku]
            workflows={str(s['id']):caps['workflow-'+str(s['id'])]['rows'][0]['data'] for s in caps['sales']['rows']}
            r=evaluate_runtime(e,product,inv,dict(rows=ledger,complete=True),caps['sales']['rows'],workflows,m.monitor.policy,
                dict(startedAt=day+'T06:20:00+00:00',completedAt=when,businessDate=day),c,opening_binding=m,scope_complete=True)
            assert r['inventoryBasis']['status']=='VERIFIED' and r['inventoryBasis']['residual']=='0'
            if day=='2026-11-14':assert r['ruleFailureCodes']==['DEMAND_DAY_COVERAGE_INCOMPLETE'] and r['demandWindow']['missingDays']==1
            if day=='2026-11-13':
                s=r['ruleResult']['supplyDemand'];assert (s['candidates'][0]['quantity'] if s['candidates'] else None)==('48' if m.sku=='HL-CBL100-2M' else None)
            records.append(dict(day=day,inventoryBasis=r['inventoryBasis'],demandWindow=r['demandWindow'],failures=r['ruleFailureCodes'],
                candidates=(r['ruleResult'] or {}).get('supplyDemand',{}).get('candidates')))
        assert all(hashlib.sha256((path/f).read_bytes()).hexdigest()==digest for f,digest in digests.items())
        summary['targets'].append(dict(sku=m.sku,sourceFiles=digests,replays=records))
    write(ROOT/'docs/evidence/S01-ADMISSION/historical.json',summary)
    if args.live:
        from dotenv import dotenv_values
        from commerce_hub.adapters.erp import ERPConfig
        from commerce_hub.data.sync.v2 import V2Reader
        from commerce_hub.data.sync.v2_catalog import collect_catalog
        from commerce_hub.data.projection.v2 import entities
        values=dotenv_values(ROOT/'.env.erp',interpolate=False);runs=[]
        for m in maps:
            private=ROOT/'data/private/admission/live'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            class Checkpoint:
                def load(self):return dict(requestCount=0)
                def save(self,v):write(private/'checkpoint.json',v)
            reader=V2Reader(ERPConfig(username=values.get('ERP_USERNAME') or '',password=values.get('ERP_PASSWORD') or '',
                access_token=values.get('ERP_ACCESS_TOKEN') or '',timeout=12),private,Checkpoint(),lambda:None,request_limit=80)
            e=dict(sourceTenant=m.sourceTenant,productId=m.monitor.productId,storeId=m.sourceStore,warehouseId=m.sourceWarehouse,
                sku=m.sku,storeName=m.storeName,warehouseName=m.warehouseName)
            catalog=collect_catalog(reader,m.sourceTenant,e,policy=m.monitor.policy)
            found=[v for v in entities(catalog,m.sourceTenant) if v['productId']==e['productId'] and v['storeId']==e['storeId'] and v['warehouseId']==e['warehouseId']]
            assert len(found)==1 and found[0]['identityVerified']
            result=analyze(catalog,found[0],reader,opening_binding=m)
            write(private/'result.json',result)
            receipt=reader.receipt()
            assert all(x['method']=='GET' or x['path']=='/api/auth-server/oauth/access-token' for x in receipt['events'])
            runs.append(dict(sku=m.sku,startedAt=receipt['startedAt'],completedAt=receipt['completedAt'],requests=receipt['requestCount'],
                events=[{k:x[k] for k in ('method','path','at','httpStatus','error','sha256') if k in x} for x in receipt['events']],
                result={k:result[k] for k in ('analysisState','sourceGrade','quantity','ruleFailureCodes','inventoryBasis','demandWindow','dataQuality','capabilities','recoveryHints')},
                businessWrites=0,models=0))
        write(ROOT/'docs/evidence/S01-ADMISSION/live.json',dict(nature='REAL_ERP_READ_ONLY_CURRENT_SOURCE',runs=runs))
    print(json.dumps(dict(result='PASS_HISTORICAL_REPLAY',live=args.live,targets=len(maps))))


if __name__=='__main__':main()
