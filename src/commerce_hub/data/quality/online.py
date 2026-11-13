"""D03 adds acquisition identity to its sole immutable input manifest."""
from copy import deepcopy
from commerce_hub.data.contracts import fingerprint
from commerce_hub.data.projection.observed import verify_observations
from commerce_hub.data.quality.observed import capture_observations
from commerce_hub.data.contracts import AdmittedInput, Issue
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture
from datetime import datetime,timedelta

def calculation_snapshot(asset):
    normalization=asset.get('normalization')
    if normalization and normalization.get('input') is not None:
        value=AdmittedInput.model_validate(normalization['input'])
        snapshot=capture(project(value,'online-'+asset['manifest']['acquisition']['acquisitionId']))
    else:
        snapshot=capture_observations(verify_observations(asset['observationProjection']))
    return snapshot.model_copy(update={'snapshotId':asset['snapshotId'],'manifest':asset['manifest'],
        'issues':tuple(Issue.model_validate(i) for i in asset['manifest']['quality'])})


def capture_online(projection, receipt, mapping_verified, normalization=None):
    if normalization and normalization.get('input') is not None:
        value=AdmittedInput.model_validate(normalization['input'])
        if value.asOf != datetime.fromisoformat(receipt['completedAt']):raise ValueError('ONLINE_ASOF_MISMATCH')
        snapshot=capture(project(value,'online-'+receipt['acquisitionId']))
    else:
        snapshot = capture_observations(verify_observations(projection))
    manifest = deepcopy(snapshot.manifest)
    manifest.pop('fingerprint')
    manifest['acquisition'] = deepcopy(receipt)
    manifest['mappingVerified'] = mapping_verified
    if normalization is not None:
        manifest['qualityVersion']='s01-online-quality-v2'
        manifest['normalizationDigest']=fingerprint(normalization)
        manifest['coverageLimitations']=normalization['assumptions']
        extras=[{k:v for k,v in i.items() if k!='category'} for i in normalization['issues']]
        if normalization.get('input') is None:
            extras.append(dict(code='QUALITY_STATE_UNKNOWN',severity='BLOCK',path='quality',affects='CANDIDATES'))
        observed_at=datetime.fromisoformat(receipt['completedAt'])
        for domain in ([] if receipt.get('monitoring') else projection['domains']):
            for time in domain['sourceTimes']:
                try:
                    source=datetime.fromisoformat(time)
                    if source.tzinfo is None:raise ValueError()
                    age=observed_at-source
                    if age<timedelta(0) or age>timedelta(hours=24):
                        extras.append(dict(code='SOURCE_DATA_STALE_OR_FUTURE',severity='BLOCK',path=domain['domain'],affects='PROVENANCE'))
                except (ValueError,TypeError):
                    extras.append(dict(code='SOURCE_TIME_INVALID',severity='BLOCK',path=domain['domain'],affects='PROVENANCE'))
        manifest['quality'] += [Issue.model_validate(i).model_dump() for i in extras]
    value = fingerprint(manifest)
    manifest['fingerprint'] = value
    asset=dict(snapshotId='snapshot-'+value, manifest=manifest, observationProjection=projection)
    if normalization is not None:asset['normalization']=deepcopy(normalization)
    return asset

def verify_asset(asset):
    expected = capture_online(asset['observationProjection'], asset['manifest']['acquisition'],asset['manifest']['mappingVerified'],asset.get('normalization'))
    if asset != expected:
        raise ValueError('ONLINE_SNAPSHOT_BINDING_REJECTED')
    return expected
