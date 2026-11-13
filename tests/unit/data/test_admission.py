"""Admission fixtures are constructed test data, never evidence of ERP network IO."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from commerce_hub.data.admission import (
    AdmissionPackage,
    AdmissionRejected,
    ENGINE_SEMANTICS,
    RuleContent,
    normalize,
    normalize_teaching,
    package_revision,
    teaching_package_revision,
    teaching_readback_content_digest,
    validate_admission,
    validate_teaching_admission,
    TeachingAdmissionConnector,
)
from commerce_hub.data.contracts import AdmittedInput, fingerprint
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture
from commerce_hub.data.sync import SourceFailure, SourcePage
from commerce_hub.capabilities.forecasting import propose
from tests.support.admission import (
    build_teaching_admission_package,
    build_test_only_admission_package,
    hand_calculated_golden_case,
)


def package():
    # This only exercises the production-shaped adapter.  The builder and refs
    # explicitly state that no ERP observation or business approval occurred.
    return build_test_only_admission_package(admittable_shape=True)


def resign(value):
    content = RuleContent.model_validate(value["rules"]["content"])
    value["rules"]["contentDigest"] = fingerprint(content.model_dump(mode="json"))


def codes(value):
    return {issue.code for issue in validate_admission(value, allow_test_only=True).issues}


def provenance(value, path):
    return next(item for item in value["provenance"] if item["fieldPath"] == path)


def teaching_codes(value):
    return {issue.code for issue in validate_teaching_admission(value).issues}


def field_value(value, path):
    parts = path.split("/")[1:]
    if parts[0] in {"scope", "policy"}:
        return value[parts[0]][parts[1]]
    if parts[0] in {"asOf", "coverageComplete", "mapping"}:
        return value[parts[0]]
    rows = value[parts[0]]
    if len(parts) == 1:
        return rows
    row = next(item for item in rows if item["recordId"] == parts[1])
    return row[parts[2]]


def rebind_teaching_readback(value, *paths):
    for path in paths:
        provenance(value, path)["valueDigest"] = fingerprint(field_value(value, path))
    value["teachingBatch"]["readBackContentDigest"] = teaching_readback_content_digest(value)
    value["teachingBatch"]["writeCanonicalContentDigest"] = value["teachingBatch"]["readBackContentDigest"]
    for artifact in value["teachingBatch"]["readBackArtifacts"]:
        artifact["contentDigest"] = fingerprint({
            "recordIds": sorted(artifact["recordIds"]),
            "fields": sorted(
                ({"fieldPath": item["fieldPath"], "valueDigest": item["valueDigest"]}
                 for item in value["provenance"]
                 if item.get("nature") == "ERP_NETWORK" and item["sourceRef"] == artifact["artifactRef"]),
                key=lambda item: item["fieldPath"],
            ),
        })
    manifest = value["teachingBatch"]
    manifest["readBackArtifactDigest"] = fingerprint({
        "batchId": manifest["readBackBatchId"],
        "operationRef": manifest["readBackOperationRef"],
        "observedAt": manifest["readBackObservedAt"],
        "artifacts": sorted(manifest["readBackArtifacts"], key=lambda item: item["alias"]),
    })


def rebind_teaching_rule(value, *paths):
    value["rules"]["content"]["policy"] = deepcopy(value["policy"])
    value["rules"]["contentDigest"] = fingerprint(
        RuleContent.model_validate(value["rules"]["content"]).model_dump(mode="json")
    )
    for path in paths:
        field = path.split("/")[-1]
        provenance(value, path)["valueDigest"] = fingerprint(value["policy"][field])


def add_teaching_derivation(value, paths, *, method="TEACHING_LAST_7_DAILY_REPLAY_V1"):
    artifact = value["teachingBatch"]["readBackArtifacts"][0]
    record_ref = "trusted-artifact:derivation-" + method.lower().replace("_", "-")
    content = {
        "method": method,
        "allowedPaths": list(paths),
        "sourceArtifactRefs": [artifact["artifactRef"]],
        "sourceContentDigests": [artifact["contentDigest"]],
        "teachingRuleRef": value["rules"]["recordRef"],
    }
    value.setdefault("derivations", []).append({
        "contentDigest": fingerprint(content),
        "content": content,
        "owner": "teaching-derivation-owner",
        "recordRef": record_ref,
        "recordedAt": "2026-11-11T00:00:00Z",
    })
    for path in paths:
        row = provenance(value, path)
        row["nature"] = "CONTROLLED_TEACHING_RULE"
        row["sourceRef"] = record_ref
        row["observedAt"] = "2026-11-11T00:00:00Z"
        row["teachingBasis"] = method
        row["derivedFromRefs"] = [artifact["artifactRef"]]
        if row["assertion"] != "COLLECTION_COMPLETE":
            row["assertion"] = "VALUE_DERIVED"


def test_normalize_returns_only_public_admitted_input_and_stable_refs():
    value = package()
    first = normalize(value, allow_test_only=True)
    second = normalize(deepcopy(value), allow_test_only=True)
    parsed = AdmittedInput.model_validate(first)
    assert first == second
    assert parsed.sourceNature == "TEACHING_ERP_OBSERVED"
    assert parsed.fixtureId == value["inputId"] == value["fixtureId"]
    assert "inputId" not in first and set(first) == {name for name, field in AdmittedInput.model_fields.items() if field.is_required()}
    assert len(first["provenanceRef"]) == len(first["rulesRef"]) == 64
    assert package_revision(value) == package_revision(AdmissionPackage.model_validate(value))


def test_constructed_non_erp_sample_adapts_into_existing_deterministic_chain():
    admitted = AdmittedInput.model_validate(normalize(package(), allow_test_only=True))
    result = propose(capture(project(admitted, "test-only-batch")))
    assert result["baseline"]["gapQuantity"] == "4"
    assert result["baseline"]["firstShortageDate"] == "2026-11-14"
    assert result["candidates"][0]["quantity"] == "5"
    assert result["candidates"][0]["evaluation"]["closingBalance"] == "1"
    assert result["candidates"][0]["procurementEligible"] is False


def test_engineering_sample_is_explicitly_blocked_and_cannot_fall_back_to_fixture_success():
    value = build_test_only_admission_package()
    decision = validate_admission(value)
    assert decision.status == "BLOCKED"
    assert {"ENGINEERING_MODE_NOT_ADMITTABLE", "REAL_SOURCE_UNADMITTED"} <= {
        issue.code for issue in decision.issues
    }
    with pytest.raises(AdmissionRejected) as rejected:
        normalize(value)
    assert any(issue.code == "ENGINEERING_MODE_NOT_ADMITTABLE" for issue in rejected.value.issues)


def test_test_only_contract_is_disabled_by_default_but_can_exercise_shape_explicitly():
    value = package()
    assert "TEST_ONLY_PACKAGE" in {issue.code for issue in validate_admission(value).issues}
    with pytest.raises(AdmissionRejected):
        normalize(value)
    assert validate_admission(value, allow_test_only=True).admitted


@pytest.mark.parametrize("nature,extra", [
    ("SIMULATED", {"testPurpose": "unit test"}),
    ("UNKNOWN", {"unknownReason": "source not confirmed"}),
])
def test_real_mode_rejects_simulated_or_unknown_required_field(nature, extra):
    value = package()
    row = provenance(value, "/demand/test-demand-1/quantity")
    row["nature"] = nature
    row.pop("factBasis", None)
    row.update(extra)
    assert "REAL_SOURCE_UNADMITTED" in codes(value)
    with pytest.raises(AdmissionRejected):
        normalize(value)


def test_controlled_fact_requires_fact_basis_and_all_source_identity_fields():
    value = package()
    provenance(value, "/demand/test-demand-1/quantity").pop("factBasis")
    assert codes(value) == {"PACKAGE_SCHEMA_INVALID"}
    for field in ("sourceVersion", "owner", "sourceRef", "observedAt"):
        changed = package()
        provenance(changed, "/demand/test-demand-1/quantity").pop(field)
        assert codes(changed) == {"PACKAGE_SCHEMA_INVALID"}


def test_teaching_source_requires_at_least_one_network_observation():
    value = package()
    row = provenance(value, "/mapping")
    row["nature"] = "CONTROLLED_FACT"
    row["factBasis"] = "Unit-test controlled mapping basis."
    assert "ERP_NETWORK_OBSERVATION_MISSING" in codes(value)


@pytest.mark.parametrize("path", [
    "/scope/tenantId",
    "/scope/canonicalSkuIds",
    "/inventory/test-inventory-1/availableQty",
    "/policy/moq",
])
def test_missing_exact_scope_fact_or_rule_provenance_blocks(path):
    value = package()
    value["provenance"] = [item for item in value["provenance"] if item["fieldPath"] != path]
    decision = validate_admission(value)
    assert any(issue.code == "REQUIRED_PROVENANCE_MISSING" and issue.path == path for issue in decision.issues)


def test_duplicate_complex_and_unexpected_provenance_paths_fail_closed():
    value = package()
    value["provenance"].append(deepcopy(provenance(value, "/asOf")))
    assert "DUPLICATE_PROVENANCE" in codes(value)
    value = package()
    value["provenance"].append(dict(deepcopy(provenance(value, "/asOf")), fieldPath="/inventory/../secret"))
    assert codes(value) == {"PACKAGE_SCHEMA_INVALID"}
    value = package()
    value["provenance"].append(dict(deepcopy(provenance(value, "/asOf")), fieldPath="/inventory/futureField"))
    assert "UNEXPECTED_PROVENANCE_PATH" in codes(value)


@pytest.mark.parametrize("path,count", [("/inventory", 0), ("/demand", 1), ("/supply", 2)])
def test_collection_completeness_record_count_must_match(path, count):
    value = package()
    provenance(value, path)["recordCount"] = count
    assert "COLLECTION_COMPLETENESS_MISMATCH" in codes(value)


def test_empty_required_collection_reports_admission_issue_even_with_completeness_record():
    value = package()
    value["demand"] = []
    value["provenance"] = [item for item in value["provenance"] if not item["fieldPath"].startswith("/demand/")]
    provenance(value, "/demand")["recordCount"] = 0
    assert "DEMAND_COLLECTION_EMPTY" in codes(value)


@pytest.mark.parametrize("path,mutate", [
    ("/inventory/test-inventory-1/availableQty", lambda value: value["inventory"][0].update(availableQty=None)),
    ("/demand/test-demand-1/quantity", lambda value: value["demand"][0].update(quantity=None)),
    ("/supply/test-supply-1/remainingQty", lambda value: value["supply"][0].update(remainingQty=None)),
    ("/supply/test-supply-1/availableDate", lambda value: value["supply"][0].update(availableDate=None)),
    ("/policy/moq", lambda value: value["policy"].update(moq=None)),
    ("/policy/qualityDisposition", lambda value: value["policy"].update(qualityDisposition="UNKNOWN")),
])
def test_required_real_values_cannot_be_unknown(path, mutate):
    value = package()
    mutate(value)
    assert any(issue.code == "REQUIRED_VALUE_UNKNOWN" and issue.path == path
               for issue in validate_admission(value).issues)


def test_provenance_observation_cannot_postdate_server_assembly():
    value = package()
    provenance(value, "/asOf")["observedAt"] = "2026-11-12T02:00:00Z"
    assert "PROVENANCE_AFTER_ASSEMBLY" in codes(value)


def test_field_value_digest_prevents_quantity_or_collection_reuse():
    value = package()
    value["demand"][0]["quantity"] = "99"
    decision = validate_admission(value, allow_test_only=True)
    mismatches = {issue.path for issue in decision.issues
                  if issue.code == "PROVENANCE_VALUE_DIGEST_MISMATCH"}
    assert "/demand/test-demand-1/quantity" in mismatches
    assert "/demand" in mismatches


@pytest.mark.parametrize("field,reference", [
    ("sourceRef", "mock:pretend-source"),
    ("sourceRef", "fixture:pretend-source"),
    ("approvalRecordRef", "simulated:pretend-approval"),
])
def test_production_admission_rejects_obvious_test_reference_schemes(field, reference):
    value = package()
    value["evidenceLevel"] = "OPERATOR_CONTROLLED"
    if field == "approvalRecordRef":
        value["rules"][field] = reference
    else:
        provenance(value, "/mapping")[field] = reference
    assert "TEST_REFERENCE_FORBIDDEN" in codes(value)


def test_rule_content_digest_binds_exact_content():
    value = package()
    value["rules"]["content"]["policy"]["moq"] = "10"
    assert "RULE_CONTENT_DIGEST_MISMATCH" in codes(value)


@pytest.mark.parametrize("fault,expected", [
    ("policy", "RULE_POLICY_MISMATCH"),
    ("scope", "RULE_SCOPE_MISMATCH"),
    ("asOf", "RULE_AS_OF_MISMATCH"),
    ("semantics", "ENGINE_SEMANTICS_UNSUPPORTED"),
    ("validity", "RULE_NOT_EFFECTIVE"),
    ("signedLater", "RULE_ATTESTATION_AFTER_ASSEMBLY"),
    ("signedAfterAsOf", "RULE_ATTESTATION_AFTER_AS_OF"),
])
def test_rule_attestation_exact_scope_time_validity_and_engine_semantics(fault, expected):
    value = package()
    if fault == "policy":
        value["rules"]["content"]["policy"]["moq"] = "10"
    elif fault == "scope":
        value["rules"]["content"]["scope"]["tenantId"] = "other-tenant"
    elif fault == "asOf":
        value["rules"]["content"]["appliesAsOf"] = "2026-11-12T00:00:01Z"
    elif fault == "semantics":
        value["rules"]["content"]["engineSemantics"] = ENGINE_SEMANTICS.replace(
            "SUPPLY_BEFORE_DEMAND", "DEMAND_BEFORE_SUPPLY"
        )
    elif fault == "validity":
        value["rules"]["effectiveUntil"] = "2026-11-12T00:00:00Z"
    elif fault == "signedLater":
        value["rules"]["signedAt"] = "2026-11-12T02:00:00Z"
    else:
        value["rules"]["signedAt"] = "2026-11-12T00:30:00Z"
    resign(value)
    assert expected in codes(value)


def test_rule_record_is_operator_provided_not_inferred_from_names_or_prefixes():
    value = package()
    value["rules"].pop("approvalRecordRef")
    assert codes(value) == {"PACKAGE_SCHEMA_INVALID"}
    value = package()
    value["rules"]["attestationKind"] = "PREFIX_IS_A_SIGNATURE"
    assert codes(value) == {"PACKAGE_SCHEMA_INVALID"}


def test_unknown_fields_and_identifier_mismatch_are_rejected():
    value = package()
    value["clientRuleOverride"] = True
    assert codes(value) == {"PACKAGE_SCHEMA_INVALID"}
    value = package()
    value["fixtureId"] = "different"
    assert "INPUT_IDENTIFIER_MISMATCH" in codes(value)


def test_teaching_mode_normalizes_with_distinct_non_operating_source_nature():
    value = build_teaching_admission_package()
    decision = validate_teaching_admission(value)
    assert decision.admitted
    result = normalize_teaching(value)
    parsed = AdmittedInput.model_validate(result)
    assert parsed.sourceNature == "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"
    assert teaching_package_revision(value) == teaching_package_revision(deepcopy(value))
    assert set(result) == {name for name, field in AdmittedInput.model_fields.items() if field.is_required()}


def test_teaching_admission_connector_is_one_complete_immutable_d01_page():
    source = build_teaching_admission_package()
    connector = TeachingAdmissionConnector(source)
    first = connector.read_page(None)
    source["inventory"][0]["availableQty"] = "999"
    second = connector.read_page(None)
    assert isinstance(first, SourcePage)
    assert first == second
    assert first.complete and first.next_cursor is None and len(first.records) == 1
    assert first.records[0]["inventory"][0]["availableQty"] == "10"
    with pytest.raises(SourceFailure, match="CURSOR_UNSUPPORTED"):
        connector.read_page("page-2")


def test_teaching_admission_connector_read_reuses_bounded_d01_then_normalizes():
    value = build_teaching_admission_package()
    admitted, batch_ref = TeachingAdmissionConnector(value).read()
    assert admitted.sourceNature == "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"
    assert admitted.fixtureId == value["fixtureId"]
    assert batch_ref == (
        "teaching-batch-" + value["teachingBatch"]["batchId"] + "-"
        + value["teachingBatch"]["readBackArtifactDigest"]
    )


def test_teaching_mode_does_not_weaken_real_analysis_entry_point():
    value = build_teaching_admission_package()
    assert validate_admission(value).status == "BLOCKED"
    with pytest.raises(AdmissionRejected):
        normalize(value)


@pytest.mark.parametrize("field", ["writeOperationRef", "writeReceiptRef", "readBackOperationRef", "readBackArtifactRef"])
def test_teaching_local_fixture_cannot_pretend_to_be_actual_io(field):
    value = build_teaching_admission_package()
    value["teachingBatch"][field] = "fixture:pretend-io"
    assert "LOCAL_ARTIFACT_NOT_READ_BACK" in teaching_codes(value)


def test_teaching_write_receipt_alone_or_reused_as_readback_is_insufficient():
    value = build_teaching_admission_package()
    value["teachingBatch"]["readBackArtifactRef"] = value["teachingBatch"]["writeReceiptRef"]
    for item in value["provenance"]:
        if item["nature"] == "ERP_NETWORK":
            item["sourceRef"] = value["teachingBatch"]["readBackArtifactRef"]
    assert "WRITE_RECEIPT_REUSED_AS_READ_BACK" in teaching_codes(value)


@pytest.mark.parametrize("fault,expected", [
    ("batch", "TEACHING_BATCH_ID_MISMATCH"),
    ("scope", "TEACHING_SOURCE_SCOPE_DIGEST_MISMATCH"),
    ("canonicalScope", "TEACHING_CANONICAL_SCOPE_DIGEST_MISMATCH"),
    ("record", "TEACHING_RECORD_IDS_MISMATCH"),
    ("content", "READ_BACK_CONTENT_DIGEST_MISMATCH"),
    ("writeContent", "WRITE_READ_CANONICAL_CONTENT_MISMATCH"),
])
def test_teaching_write_readback_identity_scope_records_and_values_must_match(fault, expected):
    value = build_teaching_admission_package()
    if fault == "batch":
        value["teachingBatch"]["readBackBatchId"] = "another-batch"
    elif fault == "scope":
        value["teachingBatch"]["readBackScopeDigest"] = "4" * 64
    elif fault == "canonicalScope":
        value["teachingBatch"]["canonicalScopeDigest"] = "4" * 64
    elif fault == "record":
        value["teachingBatch"]["readBackRecordIds"] = ["another-record"]
    elif fault == "content":
        value["inventory"][0]["availableQty"] = "99"
        provenance(value, "/inventory/test-inventory-1/availableQty")["valueDigest"] = fingerprint("99")
    else:
        value["teachingBatch"]["writeCanonicalContentDigest"] = "8" * 64
    assert expected in teaching_codes(value)


def test_teaching_field_provenance_binds_exact_readback_or_controlled_rule_artifact():
    value = build_teaching_admission_package()
    provenance(value, "/demand/test-demand-1/quantity")["sourceRef"] = "trusted-artifact:other-read"
    assert "TEACHING_PROVENANCE_REFERENCE_MISMATCH" in teaching_codes(value)
    value = build_teaching_admission_package()
    row = provenance(value, "/policy/moq")
    row["nature"] = "ERP_NETWORK"
    row.pop("teachingBasis")
    row["sourceRef"] = value["teachingBatch"]["readBackArtifactRef"]
    assert "TEACHING_PROVENANCE_NATURE_MISMATCH" in teaching_codes(value)


def test_teaching_resource_artifact_digest_binds_record_ids_and_field_values():
    value = build_teaching_admission_package()
    value["teachingBatch"]["readBackArtifacts"][0]["contentDigest"] = "9" * 64
    assert "RESOURCE_CONTENT_DIGEST_MISMATCH" in teaching_codes(value)


def test_teaching_demand_and_planned_supply_may_use_explicit_bounded_derivations():
    value = build_teaching_admission_package()
    demand_paths = [
        path for path in (item["fieldPath"] for item in value["provenance"])
        if path == "/demand" or path.startswith("/demand/")
    ]
    supply_paths = [
        path for path in (item["fieldPath"] for item in value["provenance"])
        if path == "/supply" or path.endswith(("/remainingQty", "/availableDate", "/status"))
    ]
    add_teaching_derivation(value, demand_paths)
    add_teaching_derivation(value, supply_paths, method="TEACHING_DRAFT_TO_PLANNED_SUPPLY_V1")
    assert validate_teaching_admission(value).admitted
    assert AdmittedInput.model_validate(normalize_teaching(value)).demand[0].quantity == 8


def test_teaching_derivation_cannot_replace_inventory_or_lose_get_lineage():
    value = build_teaching_admission_package()
    add_teaching_derivation(value, ["/inventory/test-inventory-1/availableQty"])
    assert "DERIVATION_PATH_FORBIDDEN" in teaching_codes(value)
    value = build_teaching_admission_package()
    add_teaching_derivation(value, ["/demand/test-demand-1/quantity"])
    provenance(value, "/demand/test-demand-1/quantity")["derivedFromRefs"] = []
    assert "DERIVATION_SOURCE_REFERENCE_MISMATCH" in teaching_codes(value)


def test_teaching_derivation_binds_method_source_digest_and_teaching_rule():
    value = build_teaching_admission_package()
    add_teaching_derivation(value, ["/demand/test-demand-1/quantity"])
    value["derivations"][0]["content"]["method"] = "CHANGED_METHOD"
    assert "DERIVATION_CONTENT_DIGEST_MISMATCH" in teaching_codes(value)
    value = build_teaching_admission_package()
    add_teaching_derivation(value, ["/demand/test-demand-1/quantity"])
    value["derivations"][0]["content"]["sourceContentDigests"] = ["7" * 64]
    value["derivations"][0]["contentDigest"] = fingerprint(value["derivations"][0]["content"])
    assert "DERIVATION_SOURCE_DIGEST_MISMATCH" in teaching_codes(value)


@pytest.mark.parametrize("quality", ["VERIFIED_CLEAR", "INVESTIGATE", "UNKNOWN"])
def test_teaching_quality_disposition_can_normalize_for_downstream_quality_gate(quality):
    value = build_teaching_admission_package()
    value["policy"]["qualityDisposition"] = quality
    rebind_teaching_rule(value, "/policy/qualityDisposition")
    assert validate_teaching_admission(value).admitted
    admitted = AdmittedInput.model_validate(normalize_teaching(value))
    snapshot = capture(project(admitted, "teaching-batch-1"))
    assert snapshot.candidates_allowed is (quality == "VERIFIED_CLEAR")


def test_teaching_unknown_required_quantity_normalizes_then_d03_blocks_calculation():
    value = build_teaching_admission_package()
    value["inventory"][0]["availableQty"] = None
    rebind_teaching_readback(value, "/inventory/test-inventory-1/availableQty", "/inventory")
    assert validate_teaching_admission(value).admitted
    admitted = AdmittedInput.model_validate(normalize_teaching(value))
    snapshot = capture(project(admitted, "teaching-batch-1"))
    assert not snapshot.calculation_allowed
    assert "UNKNOWN_OR_NEGATIVE_INVENTORY" in {issue.code for issue in snapshot.issues}


def test_golden_catalog_uses_independent_daily_and_constraint_arithmetic():
    path = Path(__file__).parents[3] / "docs/evidence/S01-BACKEND/admission/teaching-golden.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    assert catalog["demandRule"]["nature"] == "CONTROLLED_TEACHING_RULE"
    assert {case["id"].split("-")[0] for case in catalog["cases"]} == {"A", "B", "C", "D", "E"}
    assert len([case for case in catalog["cases"] if case["id"].startswith("D-")]) >= 4
    for case in catalog["cases"]:
        # This oracle imports neither production metrics (B01) nor forecasting (B02).
        assert hand_calculated_golden_case(
            opening=case["input"]["opening"],
            demand=case["input"]["demand"],
            supply=case["input"]["supply"],
            moq=case["input"]["moq"],
            order_multiple=case["input"]["orderMultiple"],
            max_order_qty=case["input"]["maxOrderQty"],
            candidate_day=case["input"]["candidateDay"],
            quality=case["input"]["quality"],
        ) == case["expected"], case["id"]
