"""Read-only DB/capture audit. No ERP/model sends; public output is an explicit projection."""
from pathlib import Path
from datetime import datetime,timezone
import os,json,hashlib,sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8');os.environ.update(COMMERCE_MODEL_PROVIDER='mock',COMMERCE_MODEL_NETWORK_ENABLED='false')
from sqlalchemy import select
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.infrastructure.database import Database,assert_migration_target
from commerce_hub.orchestration.tables import budgets,attempts,tasks
from commerce_hub.governance.observability.tables import usage_facts,audit_events
from commerce_hub.data.sync.v2_store import acquisitions
from commerce_hub.scenarios.s01_v2.store import ItemStore
from commerce_hub.scenarios.s01_v2.analysis import statistics
from commerce_hub.data.contracts import fingerprint
root=Path(__file__).resolve().parents[1];private=root/'data/private/s01-v2-local';out=root/'docs/evidence/S01-V2';out.mkdir(exist_ok=True)
settings=load_settings();assert_migration_target(settings);db=Database(settings)
summary=dict(result='PASS',capturedAt=datetime.now(timezone.utc).isoformat(),auditNature='READ_ONLY_DB_AND_SHA256_CAPTURE_REPLAY',tasks=[])
try:
 for filename in ['live-batch.json','live-single-task.json','final-batch.json','fallback-single-task.json']:
  file=private/filename
  if not file.exists():continue
  task=json.loads(file.read_text(encoding='utf-8'));key=dict(tenant_id=task['taskRef']['tenantId'],task_id=task['taskRef']['taskId'])
  with db.engine.connect() as c:
   a=c.execute(select(acquisitions).filter_by(**key)).mappings().one()
   b=c.execute(select(budgets).filter_by(**key)).mappings().one()
   model=list(c.execute(select(attempts).filter_by(**key)).mappings());usage=list(c.execute(select(usage_facts).filter_by(**key)).mappings())
   results=ItemStore.read(c,key['tenant_id'],key['task_id'])
   task_row=c.execute(select(tasks).filter_by(**key)).mappings().one()
   completed=c.execute(select(audit_events.c.occurred_at).filter_by(**key,action='TASK_COMPLETED').order_by(audit_events.c.occurred_at.desc())).scalar()
  assert task_row['state']=='SUCCEEDED' and task_row['scenario_id']==task['scenarioId']
  state=a['content'];rawdir=root/'data/private/s01-v2'/key['tenant_id']/key['task_id'];catalog={};verified=set()
  for name,resource in state['resources'].items():
   rows=[]
   for page in resource['pages']:
    raw=(rawdir/page['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==page['sha256'];verified.add(page['sha256']);d=json.loads(raw)
    rows+= [d] if resource['binding']['detail'] else d['items']
   catalog[name]=rows
  assert a['request_count']==len(state['events'])
  # Auth endpoint is read from the fixed existing connector, without exposing credentials.
  from commerce_hub.adapters.erp import AUTH_PATH
  business=[e for e in state['events'] if e['method']!='GET' and e['path']!=AUTH_PATH]
  assert not business
  record=dict(evidenceFile=filename,taskRef=task['taskRef'],scenarioId=task['scenarioId'],requestCount=a['request_count'],requestLimit=400,
   taskCreatedAt=task_row['created_at'].isoformat()+'Z',taskCompletedAt=completed.isoformat()+'Z' if completed else None,
   taskElapsedSeconds=(completed-task_row['created_at']).total_seconds() if completed else None,
   verifiedResponseFiles=len(verified),httpStatuses=dict(Counter(str(e.get('httpStatus',e.get('error','UNKNOWN'))) for e in state['events'])),
   modelAttempts=len(model),usageFacts=len(usage),usedCalls=b['used_calls'],reservedCalls=b['reserved_calls'],businessMutations=len(business),
   sourceResourceCounts={n:dict(rows=len(rows),complete=state['resources'][n]['complete'],total=state['resources'][n]['total']) for n,rows in catalog.items()},
   requestEvents=[{k:e[k] for k in ['method','path','at','completedAt','httpStatus','sha256','error'] if k in e} for e in state['events']])
  if task['scenarioId']=='S01_V2_BATCH':
   assert not model and not usage and b['used_calls']==b['reserved_calls']==0
   source_skus={r['sku'] for n in ['products','inventory','suggestions'] for r in catalog[n] if isinstance(r.get('sku'),str) and r['sku']}
   result_skus={r['sku'] for r in results.values()}
   assert source_skus==result_skus and all(r['analysisState']!='PENDING' for r in results.values())
   record.update(summary=statistics(results.values()),independentUniqueSourceSkuCount=len(source_skus),missingSkus=0,resultIntegrityDigest=fingerprint(results),
    targetFive=[dict(sku=sku,results=[{k:r.get(k) for k in ['storeId','warehouseId','productId','sourceGrade','analysisState','quantity','sourceQuantity','sourceSuggestionCount','sourceSuggestions','formalPurchases','unit','inventory','uncertainties']} for r in results.values() if r['sku']==sku],
     nativeSuggestions=[{k:r.get(k) for k in ['id','recommendation_no','sku','store_name','suggested_qty','daily_sales','local_available','overseas_available','fba_available','inbound','urgency','stockout_date','status_text','created_at','updated_at','generated_at']} for r in catalog['suggestions'] if r['sku']==sku]) for sku in ['YF-SO-NG-OS','YF-SO-PZ-L','YF-SO-QD-S','YF-SO-QD-L','YF-SO-PZ-M']],
    ownedTwo=[{k:r.get(k) for k in ['sku','quantity','sourceGrade','analysisState','formalPurchases']} for r in results.values() if r['sku'] in ['HL-CBL100-2M','HL-MUG350-WH']])
  else:
   record.update(usage=[{k:u[k] for k in ['tokens','input_tokens','output_tokens','cost','currency','pricing_version']} for u in usage],reservedCost=str(b['reserved_cost']))
  summary['tasks'].append(record)
finally:db.close()
if not summary['tasks']:raise SystemExit('NOT_RUN: no private live task references; no ERP/model requests sent')
(out/'live-audit.json').write_bytes((json.dumps(summary,ensure_ascii=False,indent=2,default=str)+'\n').encode('utf-8'))
print(json.dumps(dict(result='PASS',tasks=[{k:r[k] for k in ['scenarioId','requestCount','modelAttempts','businessMutations']} for r in summary['tasks']]),ensure_ascii=False))
