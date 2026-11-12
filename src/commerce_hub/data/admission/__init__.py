"""Strict S01 source/rule admission before the existing D02/D03/B01/B02 chain.

This module verifies an already server-assembled package.  It does not read ERP,
approve business rules, or turn engineering fixtures into observed facts.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, ValidationError, model_validator

from commerce_hub.data.contracts import (
    AdmittedInput,
    AdmittedPolicy,
    Contract,
    Demand,
    Identifier,
    Inventory,
    Mapping,
    Supply,
    UtcTimestamp,
    fingerprint,
)
from commerce_hub.data.sync import SourceFailure, SourcePage, read_pages


ENGINE_SEMANTICS = (
    "NET_AVAILABLE;INCREMENTAL_EXCLUDES_RESERVED;D1_AFTER_D0;"
    "SUPPLY_BEFORE_DEMAND;BACKLOG;BUFFER_INCLUDED"
)
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
FieldPath = Annotated[
    str,
    Field(
        min_length=2,
        max_length=160,
        pattern=r"^/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*$",
    ),
]
EvidenceRef = Annotated[
    str,
    Field(
        min_length=3,
        max_length=256,
        pattern=r"^[A-Za-z][A-Za-z0-9+.-]*:[A-Za-z0-9][A-Za-z0-9._~:/#?=&%-]*$",
    ),
]


class AdmissionScope(Contract):
    tenantId: Identifier
    canonicalSkuIds: tuple[Identifier, ...] = Field(min_length=1, max_length=1)
    storeIds: tuple[Identifier, ...] = Field(min_length=1, max_length=1)
    warehouseIds: tuple[Identifier, ...] = Field(min_length=1, max_length=1)
    fields: tuple[Literal["quantity"], ...] = Field(min_length=1, max_length=1)


class FieldProvenance(Contract):
    fieldPath: FieldPath
    assertion: Literal["VALUE_OBSERVED", "COLLECTION_COMPLETE", "RULE_VALUE"]
    nature: Literal["ERP_NETWORK", "CONTROLLED_FACT", "SIMULATED", "UNKNOWN"]
    sourceVersion: Identifier
    owner: Identifier
    sourceRef: EvidenceRef
    observedAt: UtcTimestamp
    valueDigest: Digest
    recordCount: int | None = Field(default=None, ge=0, strict=True)
    factBasis: str | None = Field(default=None, min_length=3, max_length=500)
    testPurpose: str | None = Field(default=None, min_length=3, max_length=200)
    unknownReason: str | None = Field(default=None, min_length=3, max_length=200)

    @model_validator(mode="after")
    def source_specific_evidence(self):
        if any(part in {".", ".."} for part in self.fieldPath.split("/")[1:]):
            raise ValueError("AMBIGUOUS_FIELD_PATH")
        if self.assertion == "COLLECTION_COMPLETE":
            if self.recordCount is None:
                raise ValueError("COLLECTION_RECORD_COUNT_REQUIRED")
        elif self.recordCount is not None:
            raise ValueError("RECORD_COUNT_ONLY_FOR_COLLECTION")
        if self.nature == "CONTROLLED_FACT" and not self.factBasis:
            raise ValueError("CONTROLLED_FACT_BASIS_REQUIRED")
        if self.nature == "SIMULATED" and not self.testPurpose:
            raise ValueError("SIMULATED_TEST_PURPOSE_REQUIRED")
        if self.nature == "UNKNOWN" and not self.unknownReason:
            raise ValueError("UNKNOWN_REASON_REQUIRED")
        return self


class RuleContent(Contract):
    scope: AdmissionScope
    appliesAsOf: UtcTimestamp
    policy: AdmittedPolicy
    engineSemantics: Annotated[str, Field(min_length=1, max_length=256)]


class RuleAttestation(Contract):
    attestationKind: Literal["OPERATOR_PROVIDED_CONTROLLED_RECORD"]
    ruleVersion: Identifier
    contentDigest: Digest
    content: RuleContent
    owner: Identifier
    approvedBy: Identifier
    approvalRecordRef: EvidenceRef
    signedAt: UtcTimestamp
    effectiveFrom: UtcTimestamp
    effectiveUntil: UtcTimestamp


class AdmissionPackage(Contract):
    packageVersion: Literal["s01-admission-package-v1"] = "s01-admission-package-v1"
    admissionMode: Literal["REAL_ANALYSIS", "ENGINEERING_TEST"]
    evidenceLevel: Literal["OPERATOR_CONTROLLED", "TEST_ONLY_CONTRACT"]
    inputId: Identifier
    fixtureId: Identifier
    assembledAt: UtcTimestamp
    scope: AdmissionScope
    asOf: UtcTimestamp
    coverageComplete: bool = Field(strict=True)
    mapping: Mapping
    inventory: tuple[Inventory, ...] = Field(max_length=4)
    demand: tuple[Demand, ...] = Field(max_length=45)
    supply: tuple[Supply, ...] = Field(max_length=30)
    policy: AdmittedPolicy
    provenance: tuple[FieldProvenance, ...] = Field(min_length=1, max_length=256)
    rules: RuleAttestation


class TeachingFieldProvenance(Contract):
    """Exact teaching-only provenance; it cannot be parsed as real admission evidence."""

    fieldPath: FieldPath
    assertion: Literal["VALUE_OBSERVED", "VALUE_DERIVED", "COLLECTION_COMPLETE", "RULE_VALUE"]
    nature: Literal["ERP_NETWORK", "CONTROLLED_TEACHING_RULE"]
    sourceVersion: Identifier
    owner: Identifier
    sourceRef: EvidenceRef
    observedAt: UtcTimestamp
    valueDigest: Digest
    recordCount: int | None = Field(default=None, ge=0, strict=True)
    teachingBasis: str | None = Field(default=None, min_length=3, max_length=500)
    derivedFromRefs: tuple[EvidenceRef, ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def teaching_source_specific_evidence(self):
        if any(part in {".", ".."} for part in self.fieldPath.split("/")[1:]):
            raise ValueError("AMBIGUOUS_FIELD_PATH")
        if self.assertion == "COLLECTION_COMPLETE":
            if self.recordCount is None:
                raise ValueError("COLLECTION_RECORD_COUNT_REQUIRED")
        elif self.recordCount is not None:
            raise ValueError("RECORD_COUNT_ONLY_FOR_COLLECTION")
        if self.nature == "CONTROLLED_TEACHING_RULE" and not self.teachingBasis:
            raise ValueError("CONTROLLED_TEACHING_RULE_BASIS_REQUIRED")
        if self.nature == "ERP_NETWORK" and (self.teachingBasis is not None or self.derivedFromRefs):
            raise ValueError("ERP_NETWORK_CANNOT_USE_TEACHING_DERIVATION")
        return self


class TeachingReadBackArtifact(Contract):
    alias: Identifier
    artifactRef: EvidenceRef
    operationRef: EvidenceRef
    rawResponseDigest: Digest
    observedAt: UtcTimestamp
    recordIds: tuple[Identifier, ...] = Field(max_length=64)
    contentDigest: Digest


class TeachingBatchEvidence(Contract):
    """Trusted-server references to distinct write and read-back artifacts."""

    batchId: Identifier
    writeBatchId: Identifier
    readBackBatchId: Identifier
    writeOperationRef: EvidenceRef
    writeReceiptRef: EvidenceRef
    writeReceiptDigest: Digest
    writeArtifactDigest: Digest
    writeCanonicalContentDigest: Digest
    readBackOperationRef: EvidenceRef
    readBackArtifactRef: EvidenceRef
    readBackArtifactDigest: Digest
    readBackObservedAt: UtcTimestamp
    readBackArtifacts: tuple[TeachingReadBackArtifact, ...] = Field(min_length=1, max_length=64)
    writeScopeDigest: Digest
    readBackScopeDigest: Digest
    canonicalScopeDigest: Digest
    writeRecordIds: tuple[Identifier, ...] = Field(min_length=1, max_length=128)
    readBackRecordIds: tuple[Identifier, ...] = Field(min_length=1, max_length=128)
    readBackContentDigest: Digest


class TeachingRuleRecord(Contract):
    """A fixed teaching rule record, without claiming formal business approval."""

    ruleVersion: Literal["teaching-s01-rules-v1"]
    contentDigest: Digest
    content: RuleContent
    owner: Identifier
    recordRef: EvidenceRef
    recordedAt: UtcTimestamp
    effectiveFrom: UtcTimestamp
    effectiveUntil: UtcTimestamp


class TeachingDerivationContent(Contract):
    method: Identifier
    allowedPaths: tuple[FieldPath, ...] = Field(min_length=1, max_length=128)
    sourceArtifactRefs: tuple[EvidenceRef, ...] = Field(min_length=1, max_length=16)
    sourceContentDigests: tuple[Digest, ...] = Field(min_length=1, max_length=16)
    teachingRuleRef: EvidenceRef

    @model_validator(mode="after")
    def aligned_sources(self):
        if len(self.sourceArtifactRefs) != len(self.sourceContentDigests):
            raise ValueError("DERIVATION_SOURCE_DIGEST_COUNT_MISMATCH")
        if len(set(self.allowedPaths)) != len(self.allowedPaths):
            raise ValueError("DERIVATION_PATH_DUPLICATE")
        if len(set(self.sourceArtifactRefs)) != len(self.sourceArtifactRefs):
            raise ValueError("DERIVATION_SOURCE_DUPLICATE")
        return self


class TeachingDerivationRule(Contract):
    contentDigest: Digest
    content: TeachingDerivationContent
    owner: Identifier
    recordRef: EvidenceRef
    recordedAt: UtcTimestamp


class TeachingAdmissionPackage(Contract):
    packageVersion: Literal["s01-teaching-admission-package-v1"] = "s01-teaching-admission-package-v1"
    admissionMode: Literal["TEACHING_SIMULATION"] = "TEACHING_SIMULATION"
    sourceNature: Literal["SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"] = (
        "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"
    )
    inputId: Identifier
    fixtureId: Identifier
    assembledAt: UtcTimestamp
    scope: AdmissionScope
    asOf: UtcTimestamp
    coverageComplete: bool = Field(strict=True)
    mapping: Mapping
    inventory: tuple[Inventory, ...] = Field(max_length=4)
    demand: tuple[Demand, ...] = Field(max_length=45)
    supply: tuple[Supply, ...] = Field(max_length=30)
    policy: AdmittedPolicy
    provenance: tuple[TeachingFieldProvenance, ...] = Field(min_length=1, max_length=256)
    teachingBatch: TeachingBatchEvidence
    rules: TeachingRuleRecord
    derivations: tuple[TeachingDerivationRule, ...] = Field(default=(), max_length=16)


class AdmissionIssue(Contract):
    code: Identifier
    path: str
    message: str


class AdmissionDecision(Contract):
    status: Literal["ADMITTED", "BLOCKED"]
    packageRevision: Digest | None
    provenanceRef: Digest | None
    rulesRef: Digest | None
    issues: tuple[AdmissionIssue, ...]

    @property
    def admitted(self) -> bool:
        return self.status == "ADMITTED"


class AdmissionRejected(ValueError):
    def __init__(self, issues: tuple[AdmissionIssue, ...]):
        self.issues = issues
        super().__init__("ADMISSION_BLOCKED:" + ",".join(issue.code for issue in issues))


def package_revision(value: AdmissionPackage | dict) -> str:
    package = value if isinstance(value, AdmissionPackage) else AdmissionPackage.model_validate(value)
    return fingerprint(package.model_dump(mode="json"))


def teaching_package_revision(value: TeachingAdmissionPackage | dict) -> str:
    package = (
        value
        if isinstance(value, TeachingAdmissionPackage)
        else TeachingAdmissionPackage.model_validate(value)
    )
    return fingerprint(package.model_dump(mode="json"))


def _rule_digest(rules: RuleAttestation) -> str:
    return fingerprint(rules.content.model_dump(mode="json"))


def _provenance_ref(package: AdmissionPackage) -> str:
    rows = sorted(
        (item.model_dump(mode="json") for item in package.provenance),
        key=lambda item: item["fieldPath"],
    )
    return fingerprint(rows)


def _rules_ref(package: AdmissionPackage) -> str:
    return fingerprint(package.rules.model_dump(mode="json"))


def _teaching_provenance_ref(package: TeachingAdmissionPackage) -> str:
    rows = sorted(
        (item.model_dump(mode="json") for item in package.provenance),
        key=lambda item: item["fieldPath"],
    )
    return fingerprint(rows)


def _teaching_rules_ref(package: TeachingAdmissionPackage) -> str:
    return fingerprint(package.rules.model_dump(mode="json"))


def _teaching_readback_content(package: TeachingAdmissionPackage) -> dict:
    """Canonical extraction the trusted server must derive from the read-back artifact."""

    return {
        "batchId": package.teachingBatch.batchId,
        "scope": package.scope.model_dump(mode="json"),
        "asOf": package.asOf.isoformat().replace("+00:00", "Z"),
        "coverageComplete": package.coverageComplete,
        "mapping": package.mapping.model_dump(mode="json"),
        "inventory": [row.model_dump(mode="json") for row in package.inventory],
        "demand": [row.model_dump(mode="json") for row in package.demand],
        "supply": [row.model_dump(mode="json") for row in package.supply],
    }


def teaching_readback_content_digest(value: TeachingAdmissionPackage | dict) -> str:
    """Digest the canonical extraction independently of raw response artifact bytes."""

    package = (
        value
        if isinstance(value, TeachingAdmissionPackage)
        else TeachingAdmissionPackage.model_validate(value)
    )
    return fingerprint(_teaching_readback_content(package))


def _untrusted_local_reference(reference: str) -> bool:
    return reference.lower().startswith(
        ("file:", "local:", "fixture:", "mock:", "simulated:", "test-only:", "offline-contract:")
    )


def _teaching_derivation_path_allowed(path: str) -> bool:
    parts = path.split("/")[1:]
    if parts == ["demand"] or parts == ["supply"]:
        return True
    if len(parts) != 3:
        return False
    if parts[0] == "demand":
        return parts[2] in {"day", "quantity", "semantics"}
    if parts[0] == "supply":
        return parts[2] in {"remainingQty", "availableDate", "status"}
    return False


def _readback_manifest_digest(batch: TeachingBatchEvidence) -> str:
    return fingerprint(
        {
            "batchId": batch.readBackBatchId,
            "operationRef": batch.readBackOperationRef,
            "observedAt": batch.readBackObservedAt.isoformat().replace("+00:00", "Z"),
            "artifacts": [
                artifact.model_dump(mode="json")
                for artifact in sorted(batch.readBackArtifacts, key=lambda item: item.alias)
            ],
        }
    )


def _required_paths(package: AdmissionPackage) -> tuple[set[str], dict[str, int]]:
    required = {
        "/scope/tenantId",
        "/scope/canonicalSkuIds",
        "/scope/storeIds",
        "/scope/warehouseIds",
        "/scope/fields",
        "/asOf",
        "/coverageComplete",
        "/mapping",
        "/inventory",
        "/demand",
        "/supply",
        "/policy/horizonDays",
        "/policy/bufferDays",
        "/policy/maxAgeHours",
        "/policy/moq",
        "/policy/orderMultiple",
        "/policy/candidateDates",
        "/policy/maxOrderQty",
        "/policy/otherConstraints",
        "/policy/qualityDisposition",
    }
    for row in package.inventory:
        base = f"/inventory/{row.recordId}"
        required.update({base + "/availableQty", base + "/sourceUpdatedAt", base + "/semantics"})
        if row.reservedQty is not None:
            required.add(base + "/reservedQty")
    for row in package.demand:
        base = f"/demand/{row.recordId}"
        required.update({base + "/day", base + "/quantity", base + "/semantics"})
    for row in package.supply:
        base = f"/supply/{row.recordId}"
        required.update(
            {
                base + "/supplyId",
                base + "/remainingQty",
                base + "/availableDate",
                base + "/status",
            }
        )
    return required, {
        "/inventory": len(package.inventory),
        "/demand": len(package.demand),
        "/supply": len(package.supply),
    }


def _field_value(payload: dict, path: str):
    parts = path.split("/")[1:]
    if parts[0] in {"scope", "policy"}:
        return payload[parts[0]][parts[1]]
    if parts[0] in {"asOf", "coverageComplete", "mapping"}:
        return payload[parts[0]]
    if parts[0] in {"inventory", "demand", "supply"}:
        rows = payload[parts[0]]
        if len(parts) == 1:
            return rows
        row = next(item for item in rows if item["recordId"] == parts[1])
        return row[parts[2]]
    raise KeyError(path)


def _schema_issues(error: ValidationError) -> tuple[AdmissionIssue, ...]:
    issues = []
    for item in error.errors(include_url=False, include_input=False):
        path = "/" + "/".join(str(part) for part in item["loc"])
        issues.append(
            AdmissionIssue(
                code="PACKAGE_SCHEMA_INVALID",
                path=path,
                message=item["msg"],
            )
        )
    return tuple(issues)


def validate_admission(
    value: AdmissionPackage | dict, *, allow_test_only: bool = False
) -> AdmissionDecision:
    try:
        package = value if isinstance(value, AdmissionPackage) else AdmissionPackage.model_validate(value)
    except ValidationError as error:
        return AdmissionDecision(
            status="BLOCKED",
            packageRevision=None,
            provenanceRef=None,
            rulesRef=None,
            issues=_schema_issues(error),
        )

    issues: list[AdmissionIssue] = []

    def block(code: str, path: str, message: str):
        issues.append(AdmissionIssue(code=code, path=path, message=message))

    if package.admissionMode != "REAL_ANALYSIS":
        block("ENGINEERING_MODE_NOT_ADMITTABLE", "/admissionMode", "Engineering packages stay on FixtureInput.")
    if package.evidenceLevel == "TEST_ONLY_CONTRACT" and not allow_test_only:
        block("TEST_ONLY_PACKAGE", "/evidenceLevel", "Test-only contract evidence is disabled by default.")
    if package.inputId != package.fixtureId:
        block("INPUT_IDENTIFIER_MISMATCH", "/fixtureId", "fixtureId must retain the package inputId.")
    if not package.coverageComplete:
        block("COVERAGE_NOT_COMPLETE", "/coverageComplete", "A real admitted package must assert complete bounded coverage.")
    if package.asOf > package.assembledAt:
        block("PACKAGE_AS_OF_AFTER_ASSEMBLY", "/asOf", "Package asOf cannot follow server assembly.")
    if len(package.inventory) != 1:
        block("INVENTORY_CARDINALITY_INVALID", "/inventory", "Exactly one mapped inventory balance is required.")
    if not package.demand:
        block("DEMAND_COLLECTION_EMPTY", "/demand", "Demand is required for deterministic evaluation.")
    for row in package.inventory:
        if row.availableQty is None:
            block("REQUIRED_VALUE_UNKNOWN", f"/inventory/{row.recordId}/availableQty", "Available inventory is required.")
    for row in package.demand:
        if row.quantity is None:
            block("REQUIRED_VALUE_UNKNOWN", f"/demand/{row.recordId}/quantity", "Daily demand is required.")
    for row in package.supply:
        if row.remainingQty is None:
            block("REQUIRED_VALUE_UNKNOWN", f"/supply/{row.recordId}/remainingQty", "Supply quantity is required.")
        if row.status == "UNKNOWN":
            block("REQUIRED_VALUE_UNKNOWN", f"/supply/{row.recordId}/status", "Supply status is required.")
        if row.status == "OPEN" and row.availableDate is None:
            block("REQUIRED_VALUE_UNKNOWN", f"/supply/{row.recordId}/availableDate", "Open supply availability is required.")
    for field in ("moq", "orderMultiple", "maxOrderQty"):
        if getattr(package.policy, field) is None:
            block("REQUIRED_VALUE_UNKNOWN", f"/policy/{field}", "Candidate constraint is required.")
    if not package.policy.candidateDates:
        block("REQUIRED_VALUE_UNKNOWN", "/policy/candidateDates", "Candidate dates are required.")
    if package.policy.qualityDisposition == "UNKNOWN":
        block("REQUIRED_VALUE_UNKNOWN", "/policy/qualityDisposition", "Quality disposition cannot be unknown.")

    mapping = package.mapping
    scope = package.scope
    if (
        scope.canonicalSkuIds != (mapping.canonicalSkuId,)
        or scope.storeIds != (mapping.storeId,)
        or scope.warehouseIds != (mapping.warehouseId,)
        or scope.fields != ("quantity",)
    ):
        block("SCOPE_MAPPING_MISMATCH", "/scope", "Exact single-SKU quantity scope must match the mapping.")

    required, collection_counts = _required_paths(package)
    payload = package.model_dump(mode="json")
    by_path: dict[str, list[FieldProvenance]] = {}
    for item in package.provenance:
        by_path.setdefault(item.fieldPath, []).append(item)
        if item.observedAt > package.assembledAt:
            block("PROVENANCE_AFTER_ASSEMBLY", item.fieldPath, "Observation time cannot follow package assembly.")
        if item.nature in {"SIMULATED", "UNKNOWN"}:
            block("REAL_SOURCE_UNADMITTED", item.fieldPath, "Real analysis forbids simulated or unknown required fields.")
        if item.sourceRef.lower().startswith(("test-only:", "fixture:", "mock:", "simulated:")):
            block("TEST_REFERENCE_FORBIDDEN", item.fieldPath, "Production admission rejects simulated reference schemes.")
    for path in sorted(required):
        rows = by_path.get(path, [])
        if not rows:
            block("REQUIRED_PROVENANCE_MISSING", path, "Required field provenance is missing.")
        elif len(rows) > 1:
            block("DUPLICATE_PROVENANCE", path, "A required field must have exactly one provenance record.")
        elif rows[0].valueDigest != fingerprint(_field_value(payload, path)):
            block("PROVENANCE_VALUE_DIGEST_MISMATCH", path, "Provenance does not bind the current canonical field value.")
    for path in sorted(set(by_path) - required):
        block("UNEXPECTED_PROVENANCE_PATH", path, "Only exact canonical field paths are accepted.")
    for path, count in collection_counts.items():
        rows = by_path.get(path, [])
        if len(rows) == 1 and (
            rows[0].assertion != "COLLECTION_COMPLETE" or rows[0].recordCount != count
        ):
            block(
                "COLLECTION_COMPLETENESS_MISMATCH",
                path,
                "Collection completeness assertion and record count must match the package.",
            )
    for path, rows in by_path.items():
        if path in collection_counts or len(rows) != 1:
            continue
        expected = "RULE_VALUE" if path.startswith("/policy/") else "VALUE_OBSERVED"
        if rows[0].assertion != expected:
            block("PROVENANCE_ASSERTION_MISMATCH", path, f"Expected {expected}.")
    if not any(item.nature == "ERP_NETWORK" for item in package.provenance):
        block("ERP_NETWORK_OBSERVATION_MISSING", "/provenance", "Teaching ERP observation is required for this source nature.")

    rules = package.rules
    if rules.approvalRecordRef.lower().startswith(("test-only:", "fixture:", "mock:", "simulated:")):
        block("TEST_REFERENCE_FORBIDDEN", "/rules/approvalRecordRef", "Production admission rejects simulated approval references.")
    if rules.contentDigest != _rule_digest(rules):
        block("RULE_CONTENT_DIGEST_MISMATCH", "/rules/contentDigest", "Rule content no longer matches its recorded digest.")
    if rules.ruleVersion != package.policy.version or rules.content.policy != package.policy:
        block("RULE_POLICY_MISMATCH", "/rules/content/policy", "Attested policy must exactly match the package policy and version.")
    if rules.content.scope != package.scope:
        block("RULE_SCOPE_MISMATCH", "/rules/content/scope", "Rule applicability must match the exact package scope.")
    if rules.content.appliesAsOf != package.asOf:
        block("RULE_AS_OF_MISMATCH", "/rules/content/appliesAsOf", "Rule applicability must bind the exact package asOf.")
    if rules.content.engineSemantics != ENGINE_SEMANTICS:
        block("ENGINE_SEMANTICS_UNSUPPORTED", "/rules/content/engineSemantics", "The fixed B01 semantics are not an exact match.")
    if rules.effectiveUntil <= rules.effectiveFrom or not (
        rules.effectiveFrom <= package.asOf < rules.effectiveUntil
    ):
        block("RULE_NOT_EFFECTIVE", "/rules", "The package asOf must fall inside a non-empty rule validity window.")
    if rules.signedAt > package.assembledAt:
        block("RULE_ATTESTATION_AFTER_ASSEMBLY", "/rules/signedAt", "The controlled attestation must exist before package assembly.")
    if rules.signedAt > package.asOf:
        block("RULE_ATTESTATION_AFTER_AS_OF", "/rules/signedAt", "The rule must be attested by the exact analysis asOf.")

    revision = package_revision(package)
    provenance_ref = _provenance_ref(package)
    rules_ref = _rules_ref(package)
    return AdmissionDecision(
        status="BLOCKED" if issues else "ADMITTED",
        packageRevision=revision,
        provenanceRef=provenance_ref,
        rulesRef=rules_ref,
        issues=tuple(issues),
    )


def validate_teaching_admission(value: TeachingAdmissionPackage | dict) -> AdmissionDecision:
    """Admit a teaching simulation only when trusted write/read-back evidence is bound."""

    try:
        package = (
            value
            if isinstance(value, TeachingAdmissionPackage)
            else TeachingAdmissionPackage.model_validate(value)
        )
    except ValidationError as error:
        return AdmissionDecision(
            status="BLOCKED",
            packageRevision=None,
            provenanceRef=None,
            rulesRef=None,
            issues=_schema_issues(error),
        )

    issues: list[AdmissionIssue] = []

    def block(code: str, path: str, message: str):
        issues.append(AdmissionIssue(code=code, path=path, message=message))

    if package.inputId != package.fixtureId:
        block("INPUT_IDENTIFIER_MISMATCH", "/fixtureId", "fixtureId must retain the package inputId.")
    if package.asOf > package.assembledAt:
        block("PACKAGE_AS_OF_AFTER_ASSEMBLY", "/asOf", "Package asOf cannot follow server assembly.")
    if len(package.inventory) != 1:
        block(
            "INVENTORY_CARDINALITY_INVALID",
            "/inventory",
            "Teaching S01 requires exactly one mapped inventory row, even when its value is unknown.",
        )

    mapping = package.mapping
    scope = package.scope
    if (
        scope.canonicalSkuIds != (mapping.canonicalSkuId,)
        or scope.storeIds != (mapping.storeId,)
        or scope.warehouseIds != (mapping.warehouseId,)
        or scope.fields != ("quantity",)
    ):
        block("SCOPE_MAPPING_MISMATCH", "/scope", "Exact single-SKU quantity scope must match the mapping.")

    batch = package.teachingBatch
    if batch.writeBatchId != batch.batchId or batch.readBackBatchId != batch.batchId:
        block(
            "TEACHING_BATCH_ID_MISMATCH",
            "/teachingBatch",
            "Write and read-back evidence must carry the same teaching batch identity.",
        )
    if batch.readBackObservedAt > package.assembledAt:
        block(
            "READ_BACK_AFTER_ASSEMBLY",
            "/teachingBatch/readBackObservedAt",
            "The read-back must complete before package assembly.",
        )
    artifact_refs = [artifact.artifactRef for artifact in batch.readBackArtifacts]
    artifact_aliases = [artifact.alias for artifact in batch.readBackArtifacts]
    if len(set(artifact_refs)) != len(artifact_refs) or len(set(artifact_aliases)) != len(artifact_aliases):
        block(
            "READ_BACK_ARTIFACT_DUPLICATE",
            "/teachingBatch/readBackArtifacts",
            "Resource artifact references and aliases must be unique within the manifest.",
        )
    if batch.readBackObservedAt != max(artifact.observedAt for artifact in batch.readBackArtifacts):
        block(
            "READ_BACK_MANIFEST_TIME_MISMATCH",
            "/teachingBatch/readBackObservedAt",
            "Manifest observation time must equal the latest resource GET observation.",
        )
    if batch.readBackArtifactDigest != _readback_manifest_digest(batch):
        block(
            "READ_BACK_MANIFEST_DIGEST_MISMATCH",
            "/teachingBatch/readBackArtifactDigest",
            "The aggregate manifest digest must bind all resource read-back entries.",
        )
    for index, artifact in enumerate(batch.readBackArtifacts):
        if artifact.observedAt > package.assembledAt:
            block(
                "READ_BACK_AFTER_ASSEMBLY",
                f"/teachingBatch/readBackArtifacts/{index}/observedAt",
                "Every resource GET must complete before package assembly.",
            )
        if _untrusted_local_reference(artifact.artifactRef) or _untrusted_local_reference(artifact.operationRef):
            block(
                "LOCAL_ARTIFACT_NOT_READ_BACK",
                f"/teachingBatch/readBackArtifacts/{index}",
                "A local fixture cannot establish a resource GET read-back.",
            )
    references = {
        "writeOperationRef": batch.writeOperationRef,
        "writeReceiptRef": batch.writeReceiptRef,
        "readBackOperationRef": batch.readBackOperationRef,
        "readBackArtifactRef": batch.readBackArtifactRef,
    }
    for field, reference in references.items():
        if _untrusted_local_reference(reference):
            block(
                "LOCAL_ARTIFACT_NOT_READ_BACK",
                f"/teachingBatch/{field}",
                "A local fixture or simulated reference cannot establish teaching ERP IO.",
            )
    if batch.writeOperationRef == batch.readBackOperationRef:
        block(
            "WRITE_READ_OPERATION_NOT_DISTINCT",
            "/teachingBatch/readBackOperationRef",
            "Write and read-back must be independently referenced operations.",
        )
    if batch.writeCanonicalContentDigest != batch.readBackContentDigest:
        block(
            "WRITE_READ_CANONICAL_CONTENT_MISMATCH",
            "/teachingBatch/writeCanonicalContentDigest",
            "Canonical content independently extracted from writes and GET read-back must match.",
        )
    if batch.writeReceiptRef == batch.readBackArtifactRef:
        block(
            "WRITE_RECEIPT_REUSED_AS_READ_BACK",
            "/teachingBatch/readBackArtifactRef",
            "A write receipt cannot be reused as the read-back artifact.",
        )

    scope_digest = fingerprint(package.scope.model_dump(mode="json"))
    if batch.writeScopeDigest != batch.readBackScopeDigest:
        block(
            "TEACHING_SOURCE_SCOPE_DIGEST_MISMATCH",
            "/teachingBatch",
            "Write and read-back must bind the same ERP source scope.",
        )
    if batch.canonicalScopeDigest != scope_digest:
        block(
            "TEACHING_CANONICAL_SCOPE_DIGEST_MISMATCH",
            "/teachingBatch/canonicalScopeDigest",
            "The canonical scope digest must bind the exact admitted scope.",
        )
    artifact_record_ids = tuple(
        sorted(record_id for artifact in batch.readBackArtifacts for record_id in artifact.recordIds)
    )
    if (
        tuple(sorted(batch.writeRecordIds)) != tuple(sorted(batch.readBackRecordIds))
        or artifact_record_ids != tuple(sorted(batch.readBackRecordIds))
        or len(set(batch.writeRecordIds)) != len(batch.writeRecordIds)
        or len(set(batch.readBackRecordIds)) != len(batch.readBackRecordIds)
        or len(set(artifact_record_ids)) != len(artifact_record_ids)
    ):
        block(
            "TEACHING_RECORD_IDS_MISMATCH",
            "/teachingBatch",
            "Write/read-back record identifiers must uniquely match the canonical package rows.",
        )
    if batch.readBackContentDigest != teaching_readback_content_digest(package):
        block(
            "READ_BACK_CONTENT_DIGEST_MISMATCH",
            "/teachingBatch/readBackContentDigest",
            "The canonical values do not match the content extracted from the read-back artifact.",
        )

    required, collection_counts = _required_paths(package)
    payload = package.model_dump(mode="json")
    by_path: dict[str, list[TeachingFieldProvenance]] = {}
    artifact_by_ref = {artifact.artifactRef: artifact for artifact in batch.readBackArtifacts}
    derivation_by_path: dict[str, TeachingDerivationRule] = {}
    derivation_by_ref: dict[str, TeachingDerivationRule] = {}
    for index, derivation in enumerate(package.derivations):
        path = f"/derivations/{index}"
        if derivation.recordRef in derivation_by_ref:
            block("DERIVATION_REFERENCE_DUPLICATE", path + "/recordRef", "Derivation references must be unique.")
        derivation_by_ref[derivation.recordRef] = derivation
        if _untrusted_local_reference(derivation.recordRef):
            block("LOCAL_RULE_RECORD_FORBIDDEN", path + "/recordRef", "Derivation record must be trusted.")
        if derivation.contentDigest != fingerprint(derivation.content.model_dump(mode="json")):
            block("DERIVATION_CONTENT_DIGEST_MISMATCH", path + "/contentDigest", "Derivation content changed.")
        if derivation.content.teachingRuleRef != package.rules.recordRef:
            block("DERIVATION_RULE_REFERENCE_MISMATCH", path + "/content/teachingRuleRef", "Derivation must bind the teaching rule record.")
        if derivation.recordedAt > package.asOf or derivation.recordedAt > package.assembledAt:
            block("DERIVATION_RECORD_TOO_LATE", path + "/recordedAt", "Derivation must exist by asOf and assembly.")
        for source_ref, source_digest in zip(
            derivation.content.sourceArtifactRefs, derivation.content.sourceContentDigests
        ):
            artifact = artifact_by_ref.get(source_ref)
            if artifact is None:
                block("DERIVATION_SOURCE_ARTIFACT_MISSING", path, "Derivation source is absent from the GET manifest.")
            elif artifact.contentDigest != source_digest:
                block("DERIVATION_SOURCE_DIGEST_MISMATCH", path, "Derivation source digest does not match its GET artifact.")
        for allowed_path in derivation.content.allowedPaths:
            if not _teaching_derivation_path_allowed(allowed_path):
                block("DERIVATION_PATH_FORBIDDEN", allowed_path, "Only bounded demand or planned-supply fields may be derived.")
            if allowed_path in derivation_by_path:
                block("DERIVATION_PATH_DUPLICATE", allowed_path, "A canonical field may have only one derivation rule.")
            derivation_by_path[allowed_path] = derivation
    for item in package.provenance:
        by_path.setdefault(item.fieldPath, []).append(item)
        if item.observedAt > package.assembledAt:
            block("PROVENANCE_AFTER_ASSEMBLY", item.fieldPath, "Observation time cannot follow package assembly.")
        derivation = derivation_by_path.get(item.fieldPath)
        expected_nature = "CONTROLLED_TEACHING_RULE" if (
            item.fieldPath.startswith("/policy/") or derivation is not None
        ) else "ERP_NETWORK"
        if item.nature != expected_nature:
            block(
                "TEACHING_PROVENANCE_NATURE_MISMATCH",
                item.fieldPath,
                f"Expected {expected_nature} for this field.",
            )
        expected_ref = (
            derivation.recordRef if derivation is not None else package.rules.recordRef
        ) if expected_nature == "CONTROLLED_TEACHING_RULE" else None
        if expected_nature == "CONTROLLED_TEACHING_RULE" and item.sourceRef != expected_ref:
            block(
                "TEACHING_PROVENANCE_REFERENCE_MISMATCH",
                item.fieldPath,
                "Field provenance must reference the exact read-back artifact or teaching rule record.",
            )
        if derivation is not None:
            if item.derivedFromRefs != derivation.content.sourceArtifactRefs:
                block(
                    "DERIVATION_SOURCE_REFERENCE_MISMATCH",
                    item.fieldPath,
                    "Derived provenance must bind the exact GET artifacts named by its rule.",
                )
            if item.observedAt != derivation.recordedAt:
                block(
                    "DERIVATION_OBSERVATION_TIME_MISMATCH",
                    item.fieldPath,
                    "Derived provenance time must match its controlled derivation record.",
                )
        elif expected_nature == "CONTROLLED_TEACHING_RULE" and item.derivedFromRefs:
            block("UNEXPECTED_DERIVATION_SOURCE", item.fieldPath, "Policy values are not ERP-derived facts.")
        if expected_nature == "ERP_NETWORK":
            artifact = artifact_by_ref.get(item.sourceRef)
            if artifact is None:
                block(
                    "TEACHING_PROVENANCE_REFERENCE_MISMATCH",
                    item.fieldPath,
                    "ERP provenance must reference a resource artifact in the read-back manifest.",
                )
            elif item.observedAt != artifact.observedAt:
                block(
                    "READ_BACK_OBSERVATION_TIME_MISMATCH",
                    item.fieldPath,
                    "ERP field provenance time must match its resource read-back artifact.",
                )
    for path in sorted(required):
        rows = by_path.get(path, [])
        if not rows:
            block("REQUIRED_PROVENANCE_MISSING", path, "Required field provenance is missing.")
        elif len(rows) > 1:
            block("DUPLICATE_PROVENANCE", path, "A required field must have exactly one provenance record.")
        elif rows[0].valueDigest != fingerprint(_field_value(payload, path)):
            block("PROVENANCE_VALUE_DIGEST_MISMATCH", path, "Provenance does not bind the canonical field value.")
    for path in sorted(set(by_path) - required):
        block("UNEXPECTED_PROVENANCE_PATH", path, "Only exact canonical field paths are accepted.")
    for path in sorted(set(derivation_by_path) - set(by_path)):
        block("DERIVATION_PATH_UNUSED", path, "Every allowed derivation path must bind one canonical provenance record.")
    for path, count in collection_counts.items():
        rows = by_path.get(path, [])
        if len(rows) == 1 and (
            rows[0].assertion != "COLLECTION_COMPLETE" or rows[0].recordCount != count
        ):
            block(
                "COLLECTION_COMPLETENESS_MISMATCH",
                path,
                "Collection completeness assertion and record count must match the package.",
            )
    for path, rows in by_path.items():
        if path in collection_counts or len(rows) != 1:
            continue
        expected_assertion = (
            "RULE_VALUE" if path.startswith("/policy/")
            else "VALUE_DERIVED" if path in derivation_by_path
            else "VALUE_OBSERVED"
        )
        if rows[0].assertion != expected_assertion:
            block("PROVENANCE_ASSERTION_MISMATCH", path, f"Expected {expected_assertion}.")
    for index, artifact in enumerate(batch.readBackArtifacts):
        fields = sorted(
            (
                {"fieldPath": item.fieldPath, "valueDigest": item.valueDigest}
                for item in package.provenance
                if (
                    item.nature == "ERP_NETWORK" and item.sourceRef == artifact.artifactRef
                ) or artifact.artifactRef in item.derivedFromRefs
            ),
            key=lambda item: item["fieldPath"],
        )
        if not fields:
            block(
                "UNUSED_READ_BACK_ARTIFACT",
                f"/teachingBatch/readBackArtifacts/{index}",
                "Every resource artifact must support at least one exact field provenance record.",
            )
        expected_content_digest = fingerprint(
            {"recordIds": sorted(artifact.recordIds), "fields": fields}
        )
        if artifact.contentDigest != expected_content_digest:
            block(
                "RESOURCE_CONTENT_DIGEST_MISMATCH",
                f"/teachingBatch/readBackArtifacts/{index}/contentDigest",
                "Resource artifact content digest must bind its record identifiers and exact field values.",
            )

    rules = package.rules
    if _untrusted_local_reference(rules.recordRef):
        block(
            "LOCAL_RULE_RECORD_FORBIDDEN",
            "/rules/recordRef",
            "The teaching rule record must be a trusted-server artifact, not a local fixture.",
        )
    if rules.contentDigest != _rule_digest(rules):
        block("RULE_CONTENT_DIGEST_MISMATCH", "/rules/contentDigest", "Rule content digest mismatch.")
    if rules.ruleVersion != package.policy.version or rules.content.policy != package.policy:
        block("RULE_POLICY_MISMATCH", "/rules/content/policy", "Teaching policy and fixed rule version must match.")
    if rules.content.scope != package.scope:
        block("RULE_SCOPE_MISMATCH", "/rules/content/scope", "Teaching rule scope must exactly match.")
    if rules.content.appliesAsOf != package.asOf:
        block("RULE_AS_OF_MISMATCH", "/rules/content/appliesAsOf", "Teaching rule asOf must exactly match.")
    if rules.content.engineSemantics != ENGINE_SEMANTICS:
        block("ENGINE_SEMANTICS_UNSUPPORTED", "/rules/content/engineSemantics", "Fixed B01 semantics differ.")
    if rules.effectiveUntil <= rules.effectiveFrom or not (
        rules.effectiveFrom <= package.asOf < rules.effectiveUntil
    ):
        block("RULE_NOT_EFFECTIVE", "/rules", "Teaching rule must be effective for the exact asOf.")
    if rules.recordedAt > package.assembledAt or rules.recordedAt > package.asOf:
        block("RULE_RECORD_TOO_LATE", "/rules/recordedAt", "Teaching rule record must exist by asOf and assembly.")

    return AdmissionDecision(
        status="BLOCKED" if issues else "ADMITTED",
        packageRevision=teaching_package_revision(package),
        provenanceRef=_teaching_provenance_ref(package),
        rulesRef=_teaching_rules_ref(package),
        issues=tuple(issues),
    )


def normalize(value: AdmissionPackage | dict, *, allow_test_only: bool = False) -> dict:
    try:
        package = value if isinstance(value, AdmissionPackage) else AdmissionPackage.model_validate(value)
    except ValidationError as error:
        raise AdmissionRejected(_schema_issues(error)) from None
    decision = validate_admission(package, allow_test_only=allow_test_only)
    if not decision.admitted:
        raise AdmissionRejected(decision.issues)
    canonical = AdmittedInput(
        sourceNature="TEACHING_ERP_OBSERVED",
        fixtureId=package.fixtureId,
        provenanceRef=decision.provenanceRef,
        rulesRef=decision.rulesRef,
        asOf=package.asOf,
        coverageComplete=package.coverageComplete,
        mapping=package.mapping,
        inventory=package.inventory,
        demand=package.demand,
        supply=package.supply,
        policy=package.policy,
    )
    return canonical.model_dump(mode="json")


def normalize_teaching(value: TeachingAdmissionPackage | dict) -> dict:
    """Normalize teaching ERP simulation without presenting it as operating fact."""

    try:
        package = (
            value
            if isinstance(value, TeachingAdmissionPackage)
            else TeachingAdmissionPackage.model_validate(value)
        )
    except ValidationError as error:
        raise AdmissionRejected(_schema_issues(error)) from None
    decision = validate_teaching_admission(package)
    if not decision.admitted:
        raise AdmissionRejected(decision.issues)
    canonical = AdmittedInput(
        sourceNature="SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP",
        fixtureId=package.fixtureId,
        provenanceRef=decision.provenanceRef,
        rulesRef=decision.rulesRef,
        asOf=package.asOf,
        coverageComplete=package.coverageComplete,
        mapping=package.mapping,
        inventory=package.inventory,
        demand=package.demand,
        supply=package.supply,
        policy=package.policy,
    )
    return canonical.model_dump(mode="json")


class TeachingAdmissionConnector:
    """D01 adapter over one immutable package assembled from prior trusted GET captures.

    This connector performs no network IO.  Its single source record is already
    bound to the write/read-back evidence verified by ``validate_teaching_admission``.
    """

    def __init__(self, value: TeachingAdmissionPackage | dict):
        self._package = (
            value
            if isinstance(value, TeachingAdmissionPackage)
            else TeachingAdmissionPackage.model_validate(value)
        )

    def read_page(self, cursor: str | None) -> SourcePage:
        if cursor is not None:
            raise SourceFailure("TEACHING_ADMISSION_CURSOR_UNSUPPORTED")
        record = self._package.model_dump(mode="json")
        return SourcePage(records=(record,), next_cursor=None, complete=True)

    def read(self) -> tuple[AdmittedInput, str]:
        records = read_pages(self, max_pages=1, max_records=1)
        if len(records) != 1:
            raise SourceFailure("TEACHING_ADMISSION_RECORD_CARDINALITY")
        canonical = AdmittedInput.model_validate(normalize_teaching(records[0]))
        batch = self._package.teachingBatch
        batch_ref = "teaching-batch-" + batch.batchId + "-" + batch.readBackArtifactDigest
        return canonical, batch_ref


__all__ = [
    "AdmissionDecision",
    "AdmissionIssue",
    "AdmissionPackage",
    "AdmissionRejected",
    "AdmissionScope",
    "ENGINE_SEMANTICS",
    "FieldProvenance",
    "RuleAttestation",
    "RuleContent",
    "TeachingAdmissionPackage",
    "TeachingBatchEvidence",
    "TeachingAdmissionConnector",
    "TeachingFieldProvenance",
    "TeachingDerivationContent",
    "TeachingDerivationRule",
    "TeachingReadBackArtifact",
    "TeachingRuleRecord",
    "normalize",
    "normalize_teaching",
    "package_revision",
    "teaching_package_revision",
    "teaching_readback_content_digest",
    "validate_admission",
    "validate_teaching_admission",
]
