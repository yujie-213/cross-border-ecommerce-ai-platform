"""Bounded current two-SKU read-only diagnosis. No models or ERP business writes."""
import argparse,json,hashlib
from datetime import datetime,timezone
from pathlib import Path
from commerce_hub.data.sync.online import OnlineMapping
from commerce_hub.data.sync.v2 import V2Reader
from commerce_hub.data.sync.v2_catalog import collect_catalog
from commerce_hub.data.projection.v2 import entities
from commerce_hub.scenarios.s01_v2.analysis import analyze
from commerce_hub.adapters.erp import ERPConfig
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',required=True,type=Path);p.add_argument('--execute-readonly',action='store_true');a=p.parse_args()
    if not a.execute_readonly:raise SystemExit('Explicit --execute-readonly required')
    mappings=[OnlineMapping.model_validate(m) for m in json.loads((a.source_root/'data/private/s01-mvp-20261113/mapping-proposed.json').read_text(encoding='utf-8'))]
    assert {m.sku for m in mappings}=={'HL-CBL100-2M','HL-MUG350-WH'}
    env=dotenv_values(ROOT/'.env.erp',interpolate=False);runs=[]
    for m in mappings:
        private=ROOT/'data/private/two-sku-fix'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        class Checkpoint:
            def load(self):return dict(requestCount=0)
            def save(self,v):save(private/'checkpoint.json',v)
        reader=V2Reader(ERPConfig(username=env.get('ERP_USERNAME') or '',password=env.get('ERP_PASSWORD') or '',
            access_token=env.get('ERP_ACCESS_TOKEN') or '',timeout=8,interval=.65),private,Checkpoint(),lambda:None,page_size=25,max_records=500,request_limit=60)
        e=dict(sourceTenant=m.sourceTenant,productId=m.monitor.productId,storeId=m.sourceStore,warehouseId=m.sourceWarehouse,
            sku=m.sku,storeName=m.storeName,warehouseName=m.warehouseName)
        cat=collect_catalog(reader,m.sourceTenant,e,policy=m.monitor.policy)
        found=next(x for x in entities(cat,m.sourceTenant) if x['productId']==e['productId'] and x['warehouseId']==e['warehouseId'] and x['storeId']==e['storeId'])
        result=analyze(cat,found,reader,opening_binding=m,requisition_authorized=False)
        # Independent positive control + empty-day query, in this same bounded
        # authorization/task. Empty realized sales != uncensored demand.
        probes=[]
        for day,end in [('2026-11-12','2026-11-13'),('2026-11-13','2026-11-14')]:
            cap=reader.resource('day-probe-'+day,'/api/v1/sales-orders',dict(view='full',store_name=m.storeName,shipping_warehouse=m.warehouseName,date_from=day,date_to=end))
            probes.append(dict(day=day,complete=cap['complete'],returnedCount=len(cap['rows']),
                matchingOrderIds=[str(r['id']) for r in cap['rows'] if r.get('order_time','').startswith(day)],
                allReturnedInRequestedDay=all(r.get('order_time','').startswith(day) for r in cap['rows']),observedAt=cap.get('observedAt')))
        save(private/'result.json',result);receipt=reader.receipt()
        assert all(x['method']=='GET' or x['path']=='/api/auth-server/oauth/access-token' for x in receipt['events'])
        runs.append(dict(sku=m.sku,startedAt=receipt['startedAt'],completedAt=receipt['completedAt'],requests=receipt['requestCount'],
            events=[{k:x[k] for k in ['method','path','at','completedAt','httpStatus','error','sha256'] if k in x} for x in receipt['events']],
            pageSize=25,maxRecords=500,dayProbes=probes,
            result={k:result.get(k) for k in ['analysisState','sourceGrade','quantity','inventory','inventoryBasis','demandWindow','capabilities','ruleFailureCodes','recoveryHints']},
            sourceProductTimes={k:cat['products']['rows'][0].get(k) for k in ['created_at','updated_at']},businessWrites=0,paidModels=0))
        print(json.dumps(dict(sku=m.sku,state=result['analysisState'],inventory=result['inventory']['available'],failures=result['ruleFailureCodes']),ensure_ascii=False),flush=True)
    save(ROOT/'docs/evidence/S01-TWO-SKU-FIX/current-read.json',dict(nature='CURRENT_REAL_ERP_READ_ONLY_TWO_OWNED_SKUS',runs=runs))


if __name__=='__main__':main()
