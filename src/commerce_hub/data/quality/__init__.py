"""D03 is the sole snapshot manifest/quality owner."""
from datetime import timedelta

from commerce_hub.data.contracts import Contract, Issue, Projection, fingerprint


class Snapshot(Contract):
    snapshotId: str
    manifest: dict
    projection: Projection
    issues: tuple[Issue, ...]

    @property
    def calculation_allowed(self):
        return not any(i.severity == "BLOCK" and i.affects == "CALCULATION" for i in self.issues)

    @property
    def candidates_allowed(self):
        return self.calculation_allowed and not any(i.severity == "BLOCK" for i in self.issues)


def capture(projection):
    value, issues = projection.input, list(projection.issues)
    def block(code, path, affects="CALCULATION"):
        issues.append(Issue(code=code, severity="BLOCK", path=path, affects=affects))
    if not value.coverageComplete:
        block("INCOMPLETE_COVERAGE", "coverageComplete")
    if len(projection.inventory) != 1:
        block("AMBIGUOUS_OR_MISSING_INVENTORY", "inventory")
    for row in projection.inventory:
        if row.availableQty is None or row.availableQty < 0:
            block("UNKNOWN_OR_NEGATIVE_INVENTORY", "inventory/" + row.recordId)
        if row.reservedQty is not None and row.reservedQty < 0:
            block("NEGATIVE_RESERVED", "inventory/" + row.recordId)
        age = value.asOf - row.sourceUpdatedAt
        if age < timedelta(0) or age > timedelta(hours=value.policy.maxAgeHours):
            block("STALE_OR_FUTURE_INVENTORY", "inventory/" + row.recordId)
    days = {value.asOf.date() + timedelta(days=i) for i in range(1, value.policy.horizonDays + value.policy.bufferDays + 1)}
    actual = [row.day for row in projection.demand]
    if set(actual) != days or len(actual) != len(days):
        block("DEMAND_WINDOW_INCOMPLETE_OR_DUPLICATE", "demand")
    for row in projection.demand:
        if row.quantity is None or row.quantity < 0:
            block("UNKNOWN_OR_NEGATIVE_DEMAND", "demand/" + row.recordId)
    for row in projection.supply:
        if row.status == "UNKNOWN":
            block("UNKNOWN_SUPPLY_STATUS", "supply/" + row.recordId)
        if row.remainingQty is None or row.remainingQty < 0:
            block("UNKNOWN_OR_NEGATIVE_SUPPLY", "supply/" + row.recordId)
        if row.status == "OPEN" and (row.availableDate is None or row.availableDate <= value.asOf.date()):
            block("UNKNOWN_OR_OVERDUE_AVAILABILITY", "supply/" + row.recordId)
        if row.status in {"RECEIVED", "CANCELLED"} and row.remainingQty != 0:
            block("CLOSED_SUPPLY_CONFLICT", "supply/" + row.recordId)
    policy = value.policy
    for field in ("moq", "orderMultiple", "maxOrderQty"):
        number = getattr(policy, field)
        if number is None or number <= 0:
            block("UNKNOWN_OR_INVALID_CONSTRAINT", "policy/" + field, "CANDIDATES")
    if not policy.candidateDates or any(d not in days for d in policy.candidateDates):
        block("UNKNOWN_OR_INVALID_CANDIDATE_DATE", "policy/candidateDates", "CANDIDATES")
    admitted = value.sourceNature in {"TEACHING_ERP_OBSERVED", "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"}
    if policy.qualityDisposition != ("VERIFIED_CLEAR" if admitted else "SAMPLE_CLEAR"):
        block("QUALITY_REQUIRES_RESOLUTION", "policy/qualityDisposition", "CANDIDATES")
    manifest = dict(contractVersion="0.1.0", projectionRevision=projection.revision,
                    sourceBatchIds=[projection.sourceBatchId], mappingVersion=value.mapping.version,
                    policyVersion=policy.version, sourceNature=value.sourceNature,
                    acquisitionMethod="VERIFIED_SOURCE_PACKAGE" if admitted else "INLINE_FIXTURE",
                    sourceEnvironment="TEACHING_ERP" if admitted else "ENGINEERING_ONLY",
                    asOf=value.asOf.isoformat(), businessKeys=dict(sku=value.mapping.canonicalSkuId,
                    store=value.mapping.storeId, warehouse=value.mapping.warehouseId),
                    quality=[i.model_dump() for i in issues], coverageComplete=value.coverageComplete,
                    atomicAcrossSystems=False)
    if admitted:
        manifest.update(provenanceRef=value.provenanceRef, rulesRef=value.rulesRef)
    digest = fingerprint(manifest)
    manifest["fingerprint"] = digest
    return Snapshot(snapshotId="snapshot-" + digest, manifest=manifest, projection=projection, issues=tuple(issues))
