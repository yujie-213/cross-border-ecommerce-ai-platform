"""D03 adds acquisition identity to its sole immutable input manifest."""
from copy import deepcopy
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.projection.observed import verify_observations
from commerce_hub.data.quality.observed import capture_observations

def capture_online(projection, receipt, mapping_verified):
    snapshot = capture_observations(verify_observations(projection))
    manifest = deepcopy(snapshot.manifest)
    manifest.pop('fingerprint')
    manifest['acquisition'] = deepcopy(receipt)
    manifest['mappingVerified'] = mapping_verified
    value = fingerprint(manifest)
    manifest['fingerprint'] = value
    return dict(snapshotId='snapshot-'+value, manifest=manifest, observationProjection=projection)

def verify_asset(asset):
    expected = capture_online(asset['observationProjection'], asset['manifest']['acquisition'],asset['manifest']['mappingVerified'])
    if asset != expected:
        raise ValueError('ONLINE_SNAPSHOT_BINDING_REJECTED')
    return expected
