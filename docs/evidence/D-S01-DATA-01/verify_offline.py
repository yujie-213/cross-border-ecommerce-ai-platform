"""Offline source/reference consistency checker; never a business admission test."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
INDEX = Path(__file__).with_name('admission-index.json')

def check():
    index = json.loads(INDEX.read_text(encoding='utf-8'))
    baseline = index['baselineCommit']
    # Verify baseline Git bytes, so primary integration may update shared ledgers later.
    for source in index['sourceFiles']:
        value = subprocess.check_output(['git', 'show', baseline + ':' + source['path']], cwd=ROOT)
        assert hashlib.sha256(value).hexdigest() == source['sha256'], source['path']
        assert len(value) == source['bytes'], source['path']
    source = json.loads(subprocess.check_output(['git', 'show', baseline + ':docs/agents/evidence/s01-erp-survey-20261111.json'], cwd=ROOT))
    live = source['liveVerification']
    observations = {x['id']: x for x in live['businessObservations']}
    assert len(observations) == len(live['businessObservations']) == 20
    assert len({(x['method'], x['path']) for x in observations.values()}) == 16
    assert sum(x['httpStatus'] == 200 for x in observations.values()) == 19
    assert len({(x['method'], x['path']) for x in observations.values() if x['httpStatus'] == 200}) == 15
    assert len({(x['method'], x['path']) for x in observations.values() if x['rowsObserved'] > 0}) == 10
    assert source['staticReviewedOperationCount'] == 24
    assert live['authenticationCalls'] == 2 and live['businessWriteCalls'] == 0
    assert live['scopeSummary']['rawIdentifiersSaved'] is False
    assert live['inventoryStoreOwnershipProven'] is False
    assert live['limitedPaginationObservation']['fullPaginationCoverageProven'] is False
    assert observations['R2-V08']['httpStatus'] == 503
    assert observations['R2-V04']['itemFieldTypes']['moq'] == 'int'
    assert observations['R2-V04']['itemFieldTypes']['default_carton_qty'] == 'int'
    assert observations['R2-V18']['itemFieldTypes']['item_list[].quantity_receive'] == 'NoneType'
    assert observations['R2-V18']['itemFieldTypes']['item_list[].expect_arrive_time'] == 'NoneType'
    assert observations['R2-V19']['itemFieldTypes']['purchase_date_local_utc'] == 'NoneType'
    assert index['controlledPackage']['ref'] is None and index['identity']['canonicalSkuId'] is None
    assert len(index['domains']) == len({x['id'] for x in index['domains']}) == 8
    for domain in index['domains']:
        assert domain['admission'] == 'BLOCKED' and domain['actualSignoff'] is None
        assert domain['missing'] and domain['signoffRoles']
        for ref in domain['observationIds']:
            assert ref in observations, ref
    assert set(index['gateDisposition'].values()) == {'BLOCKED'}
    assert index['safety'] == dict(newErpAuthenticationCalls=0,newErpNetworkCalls=0,realModelCalls=0,procurementWrites=0,databaseCalls=0,secretValuesRead=False,untrackedYamlRead=False)
    text = (ROOT / index['reportRef']).read_text(encoding='utf-8')
    import re
    for target in re.findall(r'\]\(([^)]+)\)', text):
        if target == 'verification.json':
            continue  # generated only after the implementation is committed
        assert (ROOT / index['reportRef']).parent.joinpath(target).exists(), target
    return dict(result='PASS',scope=index['scope'],baselineCommit=baseline,sourceFingerprints=len(index['sourceFiles']),domains=8,observationLocators=sum(len(x['observationIds']) for x in index['domains']),businessAdmission='BLOCKED',independentBusinessReview='NOT_RUN')

if __name__ == '__main__':
    print(json.dumps(check(), ensure_ascii=False))
