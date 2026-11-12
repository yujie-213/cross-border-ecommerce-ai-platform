"""Recompute teaching Golden cases from fixed API GET captures; no ERP/model requests."""
import argparse
from copy import deepcopy
from datetime import date,datetime,timedelta,timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from commerce_hub.scenarios.s01_backend import S01BackendHandler
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture
from commerce_hub.capabilities.forecasting import propose
from tools.s01_teaching_dataset import derive_policy_case

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('catalog_path', help='Final fixed catalog under data/private/')
args=parser.parse_args()
catalog_path=Path(args.catalog_path).resolve()
assert catalog_path.is_relative_to((ROOT/'data/private').resolve())
catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
entries={row['caseId']:{k:row[k] for k in ('kind','payload')} for row in catalog['entries']}
golden_path=ROOT/'docs/evidence/S01-BACKEND/admission/teaching-golden.json'
golden=json.loads(golden_path.read_text(encoding='utf-8'))
rows=[]
for oracle in golden['cases']:
    case_id=oracle['id'];expected=oracle['expected'];inputs=oracle['input']
    basis='ACTUAL_TEACHING_GET_PLUS_VERSIONED_RULE'
    if case_id in {'A','B','C'}:
        entry=entries[case_id]
    elif case_id=='E-QUALITY':
        entry=entries['E'];basis='ACTUAL_QUALITY_GET_PLUS_CONTROLLED_RULE'
    elif case_id.startswith('D-'):
        day=(date(2026,11,12)+timedelta(days=inputs['candidateDay'])).isoformat()
        package=derive_policy_case(entries['A']['payload'],case_id=case_id,
            policy_overrides=dict(moq=str(inputs['moq']),orderMultiple=str(inputs['orderMultiple']),
                maxOrderQty=str(inputs['maxOrderQty']),candidateDates=[day]))
        entry=dict(kind='TEACHING_SIMULATION',payload=package)
        basis='A_GET_PLUS_CONTROLLED_GOLDEN_RULE_RECALCULATION'
    elif case_id=='E-DATA':
        value,_=S01BackendHandler._prepare(entries['A'])
        inventory=value.inventory[0].model_copy(update={'availableQty':None})
        value=value.model_copy(update={'inventory':(inventory,)})
        snapshot=capture(project(value,'offline-negative-missing-quantity'))
        supply=propose(snapshot)
        assert not snapshot.calculation_allowed and supply['baseline'] is None and not supply['candidates']
        assert supply['limitations']==['DATA_QUALITY_BLOCKED']
        rows.append(dict(caseId=case_id,result='PASS',basis='OFFLINE_NORMALIZED_INPUT_NEGATIVE_NOT_ERP_MISSING_FACT',
            expected=expected,actual=dict(baseline=None,candidates=[],qualityCodes=[i.code for i in snapshot.issues])))
        continue
    else:
        raise AssertionError('Unexpected Golden case')
    result=S01BackendHandler._rules_result(entry,entry['payload']['scope'])
    supply=result.dataReport['supplyDemand'];baseline=supply['baseline'];candidates=supply['candidates']
    assert baseline is not None
    balances=[row['closingBalance'] for row in baseline['series']]
    assert balances==expected['baselineBalances'],case_id
    assert baseline['gapQuantity']==expected['gapQuantity'],case_id
    start=date.fromisoformat(baseline['series'][0]['day'])
    shortage=baseline['firstShortageDate']
    shortage_day=(date.fromisoformat(shortage)-start).days+1 if shortage else None
    assert shortage_day==expected['firstStockoutDay'],case_id
    outcome=expected['constraintOutcome']
    if outcome in {'NO_REPLENISHMENT_NEEDED','INTERMEDIATE_SHORTAGE_POLICY_UNDEFINED','NO_FEASIBLE_QUANTITY'}:
        assert not candidates and outcome in supply['limitations'],case_id
    elif outcome=='QUALITY_REQUIRES_RESOLUTION':
        assert not candidates and any(q['code']==outcome for q in result.dataReport['quality'])
    else:
        assert len(candidates)==1 and candidates[0]['quantity']==expected['candidateQuantity'],case_id
        evaluation=candidates[0]['evaluation']
        assert [row['closingBalance'] for row in evaluation['series']]==expected['candidateBalances'],case_id
        shortage=evaluation['firstShortageDate']
        candidate_shortage=(date.fromisoformat(shortage)-start).days+1 if shortage else None
        assert candidate_shortage==expected['candidateFirstStockoutDay'],case_id
    rows.append(dict(caseId=case_id,result='PASS',basis=basis,sourceNature=result.sourceNature,
        snapshotRef=result.snapshotRef,completeness=result.completeness,expected=expected,
        actual=dict(baseline=baseline,candidates=candidates,limitations=supply['limitations'],qualityCodes=[q['code'] for q in result.dataReport['quality']]),
        procurementEligible=False))
output=dict(schemaVersion='s01-teaching-b01-b02-golden-comparison-v1',result='PASS',
    capturedAt=datetime.now(timezone.utc).isoformat(),testedCommit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    command='python -m tools.verify_s01_teaching_golden <private-catalog>',oracleRef='docs/evidence/S01-BACKEND/admission/teaching-golden.json',
    oracleSha256=hashlib.sha256(golden_path.read_bytes()).hexdigest(),oracleGeneratedByB01B02=False,
    erpRequestsThisRun=0,modelRequests=0,rows=rows,enterpriseAdmission='BLOCKED',
    limitations=['D variants change teaching rules over A GET facts; they are not additional ERP writes.',
        'E-DATA is an explicit offline negative. E-QUALITY is backed by a distinct ERP quality GET.',
        'Draft planned supply is teaching derivation, not submitted procurement or in-transit stock.'])
target=ROOT/'docs/evidence/S01-BACKEND/teaching-data/calculation-comparison.json'
target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(result='PASS',caseCount=len(rows),cases=[r['caseId'] for r in rows],testedCommit=output['testedCommit'])))
