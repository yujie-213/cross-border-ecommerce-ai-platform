"""Offline observations of unchanged components, never ERP business evidence."""
from copy import deepcopy
from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from tests.support.s01 import example, snapshot
from tests.unit.data.test_owned import owned_case, calculate
from commerce_hub.capabilities.forecasting import propose

out = dict(sourceNature='SIMULATED_ENGINEERING', networkCalls=0, algorithmModified=False,
           erpPartialReceiptVerified=False, scenarios={}, ownedStatusMapping={})


def run(name, value):
    snap = snapshot(value)
    result = propose(snap)
    baseline = result['baseline']
    summary = dict(issues=[i.code for i in snap.issues], limitations=result['limitations'],
                   candidateQuantities=[c['quantity'] for c in result['candidates']])
    if baseline:
        summary.update({k: baseline[k] for k in ['availableQuantity','inTransitQuantity','gapQuantity',
            'stockoutRisk','firstShortageDate','closingBalance']})
    out['scenarios'][name] = summary
    return summary


base = example()
base['policy'].update(moq='12', orderMultiple='8')
line = deepcopy(base['supply'][0])
base['supply'] = []
assert run('01_no_purchase', base)['candidateQuantities'] == ['40']
v = deepcopy(base)
v['supply'] = [dict(line, remainingQty='48')]
assert run('04_timely_ordered_assumed_open', v)['candidateQuantities'] == []
v['supply'][0]['availableDate'] = '2026-11-21'
r = run('05_late_ordered_assumed_open', v)
assert r['gapQuantity'] == '0' and r['stockoutRisk']
assert r['limitations'] == ['INTERMEDIATE_SHORTAGE_POLICY_UNDEFINED']
v = deepcopy(base)
v['inventory'][0]['availableQty'] = '71'  # hypothetical original 55 + posted 16
v['supply'] = [dict(line, remainingQty='32')]
r = run('06_partial_assumed_16_sellable_32_remaining', v)
assert r['inTransitQuantity'] == '32' and r['closingBalance'] == '13'
v = deepcopy(base)
v['supply'] = [dict(line, remainingQty='0', status='CANCELLED')]
assert run('07_canonical_cancelled', v)['inTransitQuantity'] == '0'
v = deepcopy(base)
v['supply'] = [dict(line, remainingQty='24'), dict(line, recordId='supply-2', supplyId='purchase-line-2', remainingQty='24')]
assert run('08_two_distinct_lines', v)['inTransitQuantity'] == '48'
v['supply'].append(dict(v['supply'][0], recordId='mirror-1'))
r = run('08_same_line_mirror_deduplicated', v)
assert r['inTransitQuantity'] == '48' and 'DUPLICATE_RECORD' in r['issues']
v['supply'][-1]['remainingQty'] = '23'
assert 'CONFLICTING_RECORD' in run('08_conflicting_mirror_blocks', v)['issues']
v = deepcopy(base)
v['supply'] = [dict(line, warehouse='foreign-warehouse')]
assert 'UNMAPPED_IDENTITY_OR_UNIT' in run('09_foreign_warehouse_blocks', v)['issues']
v = deepcopy(base)
v['supply'] = [dict(line, status='UNKNOWN')]
assert 'UNKNOWN_SUPPLY_STATUS' in run('10_unknown_changed_state_blocks_if_observed', v)['issues']
for state in ['待提交', '待审核', '已取消', '已驳回', '待下单', '已下单', '部分收货', '已完成']:
    case = owned_case()
    case[1]['purchases']['rows'][0]['status_text'] = state
    normalized, result = calculate(case)
    out['ownedStatusMapping'][state] = dict(inputAvailable=normalized['input'] is not None,
        issues=[i['code'] for i in normalized['issues']],
        inTransitQuantity=(result.dataReport['supplyDemand'].get('baseline') or {}).get('inTransitQuantity'))
assert out['ownedStatusMapping']['待提交']['inTransitQuantity'] == '0'
assert out['ownedStatusMapping']['待审核']['inTransitQuantity'] == '0'
assert not out['ownedStatusMapping']['已驳回']['inputAvailable']
out['notImplemented'] = ['pending_approval_submission_guard', 'fresh_pre_submit_ERP_revalidation',
                         'ERP_purpose_and_store_mapping', 'owned_approved_and_partial_supply_normalization']
out['result'] = 'PASS_OFFLINE_OBSERVATIONS_ONLY'
(Path(__file__).parent/'offline-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(result=out['result'], canonicalCases=len(out['scenarios']), ownedStates=len(out['ownedStatusMapping']))))
