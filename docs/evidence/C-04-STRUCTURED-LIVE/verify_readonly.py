"""Explicit SELECT-only verification of this paid evaluation; no model/ERP requests or writes."""
from pathlib import Path
import hashlib,json,os,subprocess,sys
if sys.argv[1:] != ['--verify']:
 print('NOT_RUN: --verify explicitly reads the authorized isolated MySQL and existing private captures; no requests/writes')
 raise SystemExit(0)
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
os.environ.update(COMMERCE_MODEL_PROVIDER='mock',COMMERCE_MODEL_NETWORK_ENABLED='false')
from sqlalchemy import select,text
from commerce_hub.bootstrap.settings import load_settings
from commerce_hub.infrastructure.database import Database,assert_migration_target
from commerce_hub.orchestration.tables import tasks,reports,budgets,attempts
from commerce_hub.governance.observability.tables import usage_facts,audit_events
from commerce_hub.orchestration.contracts import DomainResult
from commerce_hub.scenarios.s01_backend.evaluation import S01ModelEvaluationHandler
from commerce_hub.scenarios.s01.natural_explanation import bundle_for_result,NaturalExplanation
from tools.s01_model_evaluation import evaluation_policy,evaluation_catalog,_catalog_evaluation_ref,STRUCTURED_AUTHORIZATION_ID

root=ROOT; private=root/'data/private/s01-c04-structured-20261112-r1'; public=root/'docs/evidence/C-04-STRUCTURED-LIVE'
w=json.loads((private/'worker.json').read_text(encoding='utf-8')); client=json.loads((private/'worker-client.json').read_text(encoding='utf-8'))
p=evaluation_policy(STRUCTURED_AUTHORIZATION_ID); ids,entries,scope=evaluation_catalog(root/'data/private/s01-teaching-dataset/S01-AI-TEST-20261112/catalog.json',private_root=root/'data/private',policy=p)
handler=S01ModelEvaluationHandler(entries,ids,scope,_catalog_evaluation_ref(STRUCTURED_AUTHORIZATION_ID,ids,entries),authorization_id=STRUCTURED_AUTHORIZATION_ID,
 case_order=p['case_order'],tenant_id=p['tenant'],principal_id=p['principal_id'],logical_namespace=p['logical_namespace'])
settings=load_settings();assert_migration_target(settings);db=Database(settings);ref=w['taskRef']
try:
 with db.engine.connect() as conn:
  def where(t):return select(t).filter_by(tenant_id=ref['tenantId'],task_id=ref['taskId'])
  task=dict(conn.execute(where(tasks)).mappings().one());budget=dict(conn.execute(where(budgets)).mappings().one())
  saved=dict(conn.execute(where(reports)).mappings().one());uses=[dict(r) for r in conn.execute(where(usage_facts)).mappings()]
  tries=[dict(r) for r in conn.execute(where(attempts)).mappings()];events=[dict(r) for r in conn.execute(where(audit_events)).mappings()]
  meta=conn.execute(text('SELECT VERSION(), DATABASE(), @@session.time_zone, @@transaction_isolation')).one()
 result=DomainResult.model_validate({k:saved['payload'][k] for k in DomainResult.model_fields})
 handler.validate_publication(result,ref,str(task['plan_version']));handler.report_view(saved['payload'])
 assert client['status']=='PASS' and task['state']=='SUCCEEDED' and len(uses)==len(tries)==5
 exchanges={x['caseId']:x['exchange'] for x in w['providerExchanges']}
 rows=[]
 for case_id,entry,row in zip(ids,entries,w['cases']):
  ai=row['analysisReport']['ai'];assert ai['status']=='AVAILABLE' and ai['reason']=='OK' and ai['costStatus']=='UNKNOWN'
  computed=handler.backend._rules_result(entry,scope); bundle=bundle_for_result(computed,ai['binding']);raw=exchanges[case_id]['content']
  parsed=bundle.validate_output(raw);assert parsed==ai['explanation']
  usage=ai['usage'];exchange=exchanges[case_id];matched=[r for r in uses if r['usage_ref']==ai['usageRef']];assert len(matched)==1
  use=matched[0];assert use['tokens']==usage['totalTokens']==exchange['input_tokens']+exchange['output_tokens']
  assert usage['inputTokens']==exchange['input_tokens'] and usage['outputTokens']==exchange['output_tokens']
  assert usage['cachedInputTokens']==exchange['cached_input_tokens'] and usage['uncachedInputTokens']==exchange['uncached_input_tokens']
  assert use['cost'] is None and usage['actualCost'] is None
  for column,key in [('input_tokens','inputTokens'),('output_tokens','outputTokens'),('cached_input_tokens','cachedInputTokens'),('uncached_input_tokens','uncachedInputTokens')]:assert use[column]==usage[key]
  supply=computed.dataReport['supplyDemand'];supplement=computed.dataReport['scenarioSupplement']
  assert supplement['procurementEligible'] is False
  baseline=supply['baseline'];candidates=supply['candidates']
  if case_id=='C':assert baseline['gapQuantity']=='0' and baseline['firstShortageDate'] and baseline['stockoutRisk'] and not candidates
  if case_id in 'BD':assert not candidates
  if case_id=='E':assert not candidates and computed.dataReport['quality']
  if case_id=='A':assert baseline['gapQuantity']=='17' and candidates[0]['quantity']=='18' and candidates[0]['evaluation']['stockoutRisk']
  unknown=[f.ref for f in bundle.context.facts if f.certainty=='UNKNOWN'];quality=next(f for f in bundle.context.facts if f.ref=='quality')
  for fact in bundle.context.facts:
   if fact.certainty=='UNKNOWN':assert all(item['text'].removesuffix(' ['+fact.ref+']') in [prefix+phrase for prefix in ['', '依据已提供事实，','根据已提供证据，','Based on the supplied fact, ','According to the supplied evidence, ','The available evidence states that '] for phrase in fact.allowedPhrases] for items in parsed.values() for item in items if item['supportRefs']==[fact.ref])
  rows.append(dict(caseId=case_id,status='AVAILABLE',schema='PASS',references='PASS',domain='PASS',versionDigests='PASS',g02ReceiptMatched=True,
   snapshotRef=row['snapshotRef'],logicalCall=handler.backend.natural_logical_call(row['snapshotRef']),usageRef=ai['usageRef'],usage=usage,
   costStatus='UNKNOWN',tokenUsageStatus=ai['tokenUsageStatus'],model=ai['actualModelRevision'],
   elapsedMs=next((e['details']['elapsedMs'] for e in events if e['details'].get('usageRef')==ai['usageRef'] and 'elapsedMs'in e['details']),None),
   originalOutputSha256=hashlib.sha256(raw.encode()).hexdigest(),promptRef=ai['versionBundle']['promptRef'],semanticPolicy=ai['semanticPolicy'],
   requiredUnknownRefs=unknown,qualityGate=quality.qualityGate,procurementEligible=False,
   deterministic=dict(gapQuantity=baseline['gapQuantity'] if baseline else None,firstShortageDate=baseline['firstShortageDate'] if baseline else None,
    stockoutRisk=baseline['stockoutRisk'] if baseline else None,candidateCount=len(candidates),candidateQuantities=[c['quantity'] for c in candidates],limitations=supply['limitations']),
   inlineCitationsPresent=sum('[' in item['text'] for items in parsed.values() for item in items)))
 totals={k:sum(row['usage'][k] for row in rows) for k in ['inputTokens','outputTokens','totalTokens','cachedInputTokens','uncachedInputTokens']}
 assert budget['used_calls']==5 and budget['used_tokens']==totals['totalTokens'] and str(budget['reserved_cost'])=='0.25000000'
 old=json.loads((root/'data/private/s01-model-evaluation-20261112/worker.json').read_text(encoding='utf-8'))
 oldcalls={e['exchange']['logical_call_id'] for e in old['providerExchanges']};assert not oldcalls & {r['logicalCall'] for r in rows}
 assert ref['taskId']!=old['taskRef']['taskId'] and task['command_key']!=('evaluation-'+hashlib.sha256(old['authorizationId'].encode()).hexdigest()[:32])
 expected=json.loads((public/'execution.json').read_text(encoding='utf-8'))
 subprocess.run(['git','diff','--exit-code',expected['testedCommit'],'--','src','tools','tests','frontend','migrations','pyproject.toml','requirements.lock'],cwd=root,check=True,stdout=subprocess.DEVNULL)
 record=dict(result='PASS',testedCommit=expected['testedCommit'],scope='New explicit S01 official DeepSeek evaluation; fixed teaching GET captures through actual API/independent Worker/O01/G02/MySQL',
  authorizationId=STRUCTURED_AUTHORIZATION_ID,taskRef=ref,reportRef=client['publishedReportRef'],taskState=task['state'],caseOrder=ids,cases=rows,totals=totals,
  paidRequests=5,implicitRetries=0,duplicateLogicalCalls=0,notRunCases=[],newActualCost=None,newCostStatus='UNKNOWN',newUnknownCostReservationUsd=str(budget['reserved_cost']),
  budget=dict(maxCalls=budget['max_calls'],maxTokens=budget['max_tokens'],maxCost=str(budget['max_cost']),usedCalls=budget['used_calls'],usedTokens=budget['used_tokens']),
  sourceCatalogPreserved=True,rawResponsesPublished=False,privateArtifactSha256=hashlib.sha256((private/'worker.json').read_bytes()).hexdigest(),
  database=dict(server=meta[0],name=meta[1],timezone=meta[2],isolation=meta[3]),
  historicalTask='192fee223c6a429d868bb584b3cf6e15',historicalEvaluation='FAIL_UNCHANGED',historicalTokens=5642,historicalReservationUsd='0.15',enterpriseGates='BLOCKED',acceptance='REVIEW')
 assert record==expected, 'LIVE_EVIDENCE_MISMATCH'
 print(json.dumps(dict(result='PASS',paidRequests=5,totals=totals,reservedUsd=str(budget['reserved_cost']),caseResults=[(r['caseId'],r['status'],r['requiredUnknownRefs'],r['qualityGate'])for r in rows])))
finally:db.close()
