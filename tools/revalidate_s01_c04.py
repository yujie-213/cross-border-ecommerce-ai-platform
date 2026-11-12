"""Revalidate unchanged private paid outputs offline; never send, account or rewrite history."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from commerce_hub.scenarios.s01.natural_explanation import (
    LEGACY_SEMANTIC_POLICY, NATURAL_SEMANTIC_POLICY, NaturalExplanation,
    bundle_for_result, validate_result_versions, validate_result_explanation,
)
from commerce_hub.scenarios.s01_backend import S01BackendHandler

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    if not args.offline:
        print('NOT_RUN: --offline required; no ERP/model/database IO')
        return 0
    worker_path = ROOT / 'data/private/s01-model-evaluation-20261112/worker.json'
    catalog_path = ROOT / 'data/private/s01-teaching-dataset/S01-AI-TEST-20261112/catalog.json'
    original_hash = hashlib.sha256(worker_path.read_bytes()).hexdigest()
    worker = json.loads(worker_path.read_text(encoding='utf-8'))
    entries = {r['caseId']: {k: r[k] for k in ('kind', 'payload')} for r in json.loads(catalog_path.read_text(encoding='utf-8'))['entries']}
    exchanges = {row['caseId']: row['exchange'] for row in worker['providerExchanges']}
    rows = []
    for row in worker['cases']:
        case_id = row['caseId']; ai = row['analysisReport']['ai']; entry = entries[case_id]
        result = S01BackendHandler([entry])._rules_result(entry, entry['payload']['scope'])
        content = exchanges[case_id]['content']
        legacy = validate_result_versions(ai, result)  # exact old refs, all six original digests
        assert legacy.semantic_policy == LEGACY_SEMANTIC_POLICY
        if ai['status'] == 'AVAILABLE':
            assert validate_result_explanation(ai, result)
        item = dict(caseId=case_id, originalContentSha256=hashlib.sha256(content.encode()).hexdigest(),
                    originalVersionDigests='PASS', originalResponseModified=False)
        NaturalExplanation.model_validate_json(content)
        item['schema'] = 'PASS'
        for name, bundle in [('legacy', legacy), ('structured', bundle_for_result(result, ai['binding']))]:
            try:
                bundle.validate_output(content)
                item[name] = dict(result='PASS', failureCode=None)
            except ValueError as exc:
                item[name] = dict(result='FAIL', failureCode=str(exc))
        rows.append(item)
    assert hashlib.sha256(worker_path.read_bytes()).hexdigest() == original_hash
    report = dict(testedCommit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        scope='Unmodified original paid A/B/C responses, offline, current computed teaching facts; no raw text published.',
        legacyPolicy=LEGACY_SEMANTIC_POLICY, policy=NATURAL_SEMANTIC_POLICY, cases=rows,
        originalPrivateArtifactSha256=original_hash, originalPrivateArtifactPreserved=True,
        historicalC04='FAIL_UNCHANGED', paidModelRequests=0, addedTokens=0,
        liveCases={k:'NOT_RUN_NEW_AUTHORIZATION_REQUIRED' for k in 'CDE'},
        actualCost=None, costStatus='UNKNOWN', historicalReservedUsd='0.15', enterpriseGates='BLOCKED')
    target = ROOT / 'docs/evidence/S01-UI-C04-FIX'
    target.mkdir(parents=True, exist_ok=True)
    (target / 'offline-revalidation.json').write_bytes((json.dumps(report, ensure_ascii=False, indent=2)+'\n').encode())
    print(json.dumps(dict(cases=rows, paidModelRequests=0, rawContentPublished=False)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
