"""D03 owns the only manifest for a currently unadmitted real-source observation."""
from commerce_hub.data.contracts import Contract, Issue, fingerprint
from commerce_hub.data.projection.observed import ObservationProjection, verify_observations

class ObservationSnapshot(Contract):
    snapshotId: str
    manifest: dict
    projection: ObservationProjection
    issues: tuple[Issue, ...]

    @property
    def calculation_allowed(self):
        # This DTO is an observation, never an implicitly approved calculation input.
        return False

    @property
    def candidates_allowed(self):
        return False


def capture_observations(projection):
    projection = verify_observations(projection.model_dump(mode="json"))
    codes = ["REAL_RULES_NOT_SIGNED", "NET_AVAILABLE_UNCONFIRMED", "SOURCE_TIMEZONE_UNCONFIRMED",
        "INVENTORY_FRESHNESS_NOT_ADMITTED", "DEMAND_COVERAGE_UNPROVEN", "SUPPLY_COVERAGE_UNPROVEN",
        "AVAILABLE_DATES_UNCONFIRMED", "MOQ_APPLICABILITY_UNCONFIRMED", "INDEPENDENT_ORDER_MULTIPLE_UNKNOWN",
        "REQUIRED_QUALITY_UNRESOLVED"]
    if projection.revalidationFailed:
        codes.append("SOURCE_REVALIDATION_FAILED")
    if not projection.ownerConfirmed:
        codes.append("PILOT_IDENTITY_NOT_CONFIRMED")
    issues = tuple(Issue(code=c, severity="BLOCK", path="admission", affects="CALCULATION") for c in codes)
    manifest = dict(contractVersion="0.1.0", projectionRevision=projection.revision,
        sourceNature=projection.sourceNature, sourceEnvironment="TEACHING_ERP", acquisitionMethod="NETWORK_READ",
        nature="OBSERVED_FACT", sourceSynthetic=projection.sourceSynthetic, revalidationFailed=projection.revalidationFailed, scope=projection.scope,
        asOf=projection.observedAt.isoformat(), atomicAcrossSystems=False,
        sourceRefs=sorted({ref for domain in projection.domains for ref in domain.sourceRefs}),
        quality=[i.model_dump() for i in issues], ruleAdmission="BLOCKED")
    value = fingerprint(manifest)
    return ObservationSnapshot(snapshotId="snapshot-"+value, manifest=dict(manifest, fingerprint=value),
        projection=projection, issues=issues)
