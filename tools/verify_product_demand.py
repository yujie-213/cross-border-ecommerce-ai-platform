"""Read-only audit of a real product batch, captures and zero ERP mutations/models."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import argparse,json,os,hashlib,sys
os.environ.update(COMMERCE_MODEL_PROVIDER='mock',COMMERCE_MODEL_NETWORK_ENABLED='false')
from sqlalchemy import select,func
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.infrastructure.database import Database,assert_migration_target
from commerce_hub.orchestration.tables import tasks,attempts,budgets
from commerce_hub.data.sync.v2_store import acquisitions
from commerce_hub.scenarios.s01_v2.store import ItemStore
from commerce_hub.scenarios.s01_v2.analysis import statistics
from commerce_hub.data.contracts import fingerprint
from commerce_hub.adapters.erp import AUTH_PATH

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--task');parser.add_argument('--partial',action='store_true');args=parser.parse_args()
    settings=load_settings();assert_migration_target(settings);db=Database(settings)
    try:
        with db.engine.connect() as c:
            query=select(tasks).filter_by(tenant_id='s01-v2-teaching-local',scenario_id='S01_V2_BATCH')
            if args.task:query=query.filter_by(task_id=args.task)
            task=c.execute(query.order_by(tasks.c.created_at.desc())).mappings().first()
            if not task:raise ValueError('NO_PRODUCT_TASK')
            key=dict(tenant_id=task['tenant_id'],task_id=task['task_id'])
            acq=c.execute(select(acquisitions).filter_by(**key)).mappings().one()
            results=ItemStore.read(c,**dict(tenant=key['tenant_id'],task=key['task_id']))
            model=c.scalar(select(func.count()).select_from(attempts).filter_by(**key))
            budget=c.execute(select(budgets).filter_by(**key)).mappings().one()
        state=acq['content'];catalog={};verified=set();rawroot=ROOT/'data/private/s01-v2'/key['tenant_id']/key['task_id']
        for name,resource in state['resources'].items():
            rows=[]
            for page in resource['pages']:
                raw=(rawroot/page['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==page['sha256'];verified.add(page['sha256']);d=json.loads(raw)
                rows.extend([d] if resource['binding']['detail'] else d['items'])
            resource_path=resource['binding']['path']
            alias={'/api/v1/products':'products','/api/v1/inventory':'inventory','/api/v1/sales-orders':'sales',
                '/api/v1/replenishment':'suggestions','/api/v1/supplier-quotes':'quotes'}.get(resource_path,name)
            catalog.setdefault(alias,[]).extend(rows)
        events=state['events'];mutations=[e for e in events if e['method']!='GET' and e['path']!=AUTH_PATH]
        assert not mutations and not model and budget['used_calls']==budget['reserved_calls']==0
        summary=statistics(results.values(),'product-counts-v1')
        counts=Counter((s.get('payment_status','MISSING'),s.get('fulfillment_status','MISSING'),s.get('refund_status','MISSING')) for s in catalog.get('sales',[]))
        output=dict(result='IN_PROGRESS' if task['state']!='SUCCEEDED' else 'PASS_READONLY_PRODUCT_BATCH',taskId=key['task_id'],taskState=task['state'],
            observedAt=datetime.now(timezone.utc).isoformat(),decisionVersion=state.get('decisionVersion'),summary=summary,
            monitoring=state.get('monitoring'),startedAt=state['startedAt'],
            acquisitionElapsedSeconds=(datetime.fromisoformat(events[-1]['completedAt'])-datetime.fromisoformat(state['startedAt'])).total_seconds(),
            requestCount=acq['request_count'],verifiedResponseFiles=len(verified),httpStatuses=dict(Counter(str(e.get('httpStatus',e.get('error','UNKNOWN'))) for e in events)),
            resourceCounts={n:dict(rows=len(rows)) for n,rows in catalog.items()},
            resourcesComplete={n:r['complete'] for n,r in state['resources'].items()},
            salesStateCounts=[dict(payment=a,fulfillment=b,refund=d,count=count) for (a,b,d),count in counts.items()],
            ownedTwo=[{k:r.get(k) for k in ['sku','storeId','warehouseId','analysisState','sourceGrade','inventory','decision','erpComparison','procurementEligibility']} for r in results.values() if r['sku'] in {'HL-CBL100-2M','HL-MUG350-WH'}],
            independentSourceSkuCount=len({r['sku'] for n in ['products','inventory','suggestions'] for r in catalog.get(n,[]) if r.get('sku')}),
            modelAttempts=model,businessWrites=len(mutations),resultDigest=fingerprint(results),
            events=[{k:e[k] for k in ['method','path','at','completedAt','httpStatus','error','sha256'] if k in e} for e in events])
        if not args.partial:
            assert task['state']=='SUCCEEDED' and state['decisionVersion']=='s01-product-demand-v1'
            assert state['monitoring']['mode']=='OWNED_REGISTERED'
            members=state['monitoring']['members']
            assert {(r['productId'],r['storeId'],r['warehouseId'],r['sku']) for r in results.values()}=={(m['productId'],m['storeId'],m['warehouseId'],m['sku']) for m in members}
            assert {str(r['id']) for r in catalog['sales']}=={sid for m in members for sid in m['salesIds']}
            assert all(output['resourcesComplete'].values())
            assert output['independentSourceSkuCount']==summary['discoveredSkuCount'] and summary['failed']==summary['unfinished']==0
            assert len(output['ownedTwo'])==2 and all(r['decision']['forecast']['available'] and r['decision']['referenceReplenishmentQuantity'] is not None for r in output['ownedTwo'])
            public=ROOT/'docs/evidence/S01-PRODUCT';public.mkdir(exist_ok=True)
            (public/'live-batch.json').write_bytes((json.dumps(output,ensure_ascii=False,indent=2)+'\n').encode())
        print(json.dumps({k:output[k] for k in ['taskId','taskState','summary','requestCount','resourceCounts','salesStateCounts']},ensure_ascii=False))
        for row in output['ownedTwo']:
            print(json.dumps(dict(sku=row['sku'],available=row['inventory']['available'],forecast=row['decision']['forecast'],referenceQuantity=row['decision']['referenceReplenishmentQuantity'],purchaseQuantity=row['decision']['purchasableQuantity']),ensure_ascii=False))
    finally:db.close()


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    main()
