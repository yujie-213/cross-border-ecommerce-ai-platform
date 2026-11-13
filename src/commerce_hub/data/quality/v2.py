"""D03 owns V2 catalog/result manifests and integrity validation."""
from copy import deepcopy
from commerce_hub.data.contracts import fingerprint


def catalog_manifest(receipt,tenant):
    body=dict(version='s01-v2-catalog-v1',sourceTenant=str(tenant),acquisition=deepcopy(receipt))
    return dict(body,snapshotRef='snapshot-'+fingerprint(body))


def seal_result(result,input_ref):
    clean={k:v for k,v in result.items() if k not in {'snapshotRef','snapshotManifest'}}
    manifest=dict(version='s01-v2-result-v1',inputSnapshotRef=input_ref,entityKey=clean['entityKey'],resultDigest=fingerprint(clean))
    return dict(clean,snapshotManifest=manifest,snapshotRef='snapshot-'+fingerprint(manifest))


def verify_result(result):
    expected=seal_result(result,result['snapshotManifest']['inputSnapshotRef'])
    if expected!=result:raise ValueError('V2_RESULT_SNAPSHOT_MISMATCH')
    return result
