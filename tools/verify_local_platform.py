"""Read-only local acceptance audit. No ERP, model or procurement sends."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,os,hashlib
os.environ.update(COMMERCE_MODEL_PROVIDER='mock',COMMERCE_MODEL_NETWORK_ENABLED='false')
from sqlalchemy import select,func
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.infrastructure.database import Database,assert_migration_target,SCHEMA_REVISION
from commerce_hub.governance.access.local import admins
from commerce_hub.data.sync.v2_store import acquisitions
from commerce_hub.scenarios.s01_v2.store import ItemStore
from commerce_hub.orchestration.tables import budgets,attempts
from commerce_hub.governance.observability.tables import usage_facts
from commerce_hub.scenarios.s01_backend.requisition_store import requisitions
from commerce_hub.adapters.erp import AUTH_PATH
ROOT=Path(__file__).resolve().parents[1];private=ROOT/'data/private/local-platform';out=ROOT/'docs/evidence/S01-LOCAL';out.mkdir(exist_ok=True)
ref=json.loads((private/'readonly-batch.json').read_text(encoding='utf-8'))['taskRef'];key=dict(tenant_id=ref['tenantId'],task_id=ref['taskId'])
settings=load_settings();assert_migration_target(settings);db=Database(settings)
try:
 with db.engine.connect() as c:
  rows=ItemStore.read(c,ref['tenantId'],ref['taskId']);a=c.execute(select(acquisitions).filter_by(**key)).mappings().one();b=c.execute(select(budgets).filter_by(**key)).mappings().one()
  model=c.scalar(select(func.count()).select_from(attempts).filter_by(**key));usage=c.scalar(select(func.count()).select_from(usage_facts).filter_by(**key))
  credential=c.execute(select(admins.c.password_hash).filter_by(tenant_id=ref['tenantId'])).scalars().all()
  previous=c.execute(select(requisitions).filter_by(tenant_id=ref['tenantId'])).mappings().all()
  all_model=list(c.execute(select(usage_facts.c.tokens).filter_by(tenant_id=ref['tenantId'])).scalars())
 assert len(credential)==1 and credential[0].startswith('scrypt-v1$')
 assert model==usage==b['used_calls']==b['reserved_calls']==0
 assert len(previous)==1 and previous[0]['content']['erpId']=='1426' and previous[0]['content']['finalQuantity']==40
 state=a['content'];catalog={};verified=set();rawroot=ROOT/'data/private/s01-v2'/ref['tenantId']/ref['taskId']
 for name,entry in state['resources'].items():
  source=[]
  for page in entry['pages']:
   raw=(rawroot/page['file']).read_bytes();assert hashlib.sha256(raw).hexdigest()==page['sha256'];verified.add(page['sha256']);d=json.loads(raw);source+= [d] if entry['binding']['detail'] else d['items']
  catalog[name]=source
 source_skus={r['sku'] for n in ['products','inventory','suggestions'] for r in catalog[n] if r.get('sku')}
 assert source_skus=={r['sku'] for r in rows.values()} and all(r['analysisState']!='PENDING' for r in rows.values())
 events=state['events'];assert len(events)==a['request_count'] and all(e['method']=='GET' or e['path']==AUTH_PATH for e in events)
 assert len(all_model)==2 and sum(all_model)==4389
 browser=json.loads((private/'browser-login-result.json').read_text(encoding='utf-8'))
 result=dict(result='PASS_LOCAL_PRODUCT_COMPATIBILITY',observedAt=datetime.now(timezone.utc).isoformat(),migrationHead=SCHEMA_REVISION,taskRef=ref,
  adminAccountsInConfiguredLocalTenant=1,passwordStorage='RANDOM_SALT_SCRYPT_N131072_R8_P1',passwordOrHashPublished=False,
  batch=dict(summary=browser['summary'],sourceLimits=browser['sourceLimits'],httpAttempts=a['request_count'],httpStatuses=dict(Counter(str(e.get('httpStatus',e.get('error','UNKNOWN'))) for e in events)),verifiedRawResponseFiles=len(verified),independentSourceSkuCount=len(source_skus),missingSkus=0,modelAttempts=model,usageFacts=usage,businessWrites=0),
  oldRealModels=dict(calls=len(all_model),tokens=sum(all_model),newPaidCalls=0,cost='UNKNOWN_UNCHANGED'),oldRequisition=dict(id='1426',savedStatus=previous[0]['content']['erpStatus'],quantity=40,rows=1,newBusinessWrites=0),
  currentRuleDataLimit=[{k:r.get(k) for k in ['sku','sourceGrade','analysisState','ruleFailureCodes']} for r in rows.values() if r['sku'] in ['HL-CBL100-2M','HL-MUG350-WH']],
  startup=dict(newBusinessTasksOnStart=0,newERPAuthOrReadsOnStart=0,newModelCallsOnStart=0,sourceEvidence='Only one new real task explicitly created in browser; all source journal requests belong to it. Supervisor checks internal health/DB only.'),
  browser=[json.loads((private/n).read_text(encoding='utf-8')) for n in ['browser-login-result.json','browser-restore-result.json','browser-expired-result.json']],launcher=json.loads((private/'launcher-result.json').read_text(encoding='utf-8')))
 (out/'live.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(result=result['result'],sourceHttp=a['request_count'],skuCount=len(source_skus),newModels=0,newProcurementWrites=0)))
finally:db.close()
