"""Contract-only admission sample; never evidence of ERP IO or rule approval."""
from copy import deepcopy
from decimal import Decimal, ROUND_CEILING

from commerce_hub.data.admission import (
    ENGINE_SEMANTICS,
    RuleContent,
    teaching_readback_content_digest,
)
from commerce_hub.data.contracts import fingerprint


def _field_value(payload, path):
    parts = path.split("/")[1:]
    if parts[0] in {"scope", "policy"}:
        return payload[parts[0]][parts[1]]
    if parts[0] in {"asOf", "coverageComplete", "mapping"}:
        return payload[parts[0]]
    rows = payload[parts[0]]
    if len(parts) == 1:
        return rows
    row = next(item for item in rows if item["recordId"] == parts[1])
    return row[parts[2]]


def build_test_only_admission_package(*, admittable_shape: bool = False) -> dict:
    """Return offline contract data, without claiming an external reference was read."""
    as_of = "2026-11-12T00:00:00Z"
    scope = dict(tenantId="test-only-tenant", canonicalSkuIds=["test-only-sku"],
        storeIds=["test-only-store"], warehouseIds=["test-only-warehouse"], fields=["quantity"])
    mapping = dict(version="test-only-mapping-v1", sourceSku="test-source-sku",
        sourceStore="test-source-store", sourceWarehouse="test-source-warehouse",
        canonicalSkuId="test-only-sku", storeId="test-only-store", warehouseId="test-only-warehouse",
        sourceUnit="EA", unit="EA", unitsPerSourceUnit="1")
    inventory = [dict(recordId="test-inventory-1", sku="test-source-sku", store="test-source-store",
        warehouse="test-source-warehouse", unit="EA", availableQty="10", reservedQty=None,
        semantics="NET_AVAILABLE", sourceUpdatedAt=as_of)]
    demand = [
        dict(recordId="test-demand-1", sku="test-source-sku", store="test-source-store",
            warehouse="test-source-warehouse", unit="EA", day="2026-11-13", quantity="8",
            semantics="INCREMENTAL_EXCLUDES_RESERVED"),
        dict(recordId="test-demand-2", sku="test-source-sku", store="test-source-store",
            warehouse="test-source-warehouse", unit="EA", day="2026-11-14", quantity="8",
            semantics="INCREMENTAL_EXCLUDES_RESERVED")]
    supply = [dict(recordId="test-supply-1", supplyId="test-po-line-1", sku="test-source-sku",
        store="test-source-store", warehouse="test-source-warehouse", unit="EA", remainingQty="2",
        availableDate="2026-11-13", status="OPEN")]
    policy = dict(version="test-only-policy-v1", horizonDays=1, bufferDays=1, maxAgeHours=24,
        moq="5", orderMultiple="5", candidateDates=["2026-11-13"], maxOrderQty="100",
        otherConstraints="REVIEWED_NOT_APPLICABLE", qualityDisposition="VERIFIED_CLEAR")
    payload = dict(scope=scope, asOf=as_of, coverageComplete=True, mapping=mapping,
        inventory=inventory, demand=demand, supply=supply, policy=policy)
    rules_content = dict(scope=deepcopy(scope), appliesAsOf=as_of, policy=deepcopy(policy),
        engineSemantics=ENGINE_SEMANTICS)
    paths = {
        "/scope/tenantId": "VALUE_OBSERVED", "/scope/canonicalSkuIds": "VALUE_OBSERVED",
        "/scope/storeIds": "VALUE_OBSERVED", "/scope/warehouseIds": "VALUE_OBSERVED",
        "/scope/fields": "VALUE_OBSERVED", "/asOf": "VALUE_OBSERVED",
        "/coverageComplete": "VALUE_OBSERVED", "/mapping": "VALUE_OBSERVED",
        "/inventory": "COLLECTION_COMPLETE",
        "/inventory/test-inventory-1/availableQty": "VALUE_OBSERVED",
        "/inventory/test-inventory-1/sourceUpdatedAt": "VALUE_OBSERVED",
        "/inventory/test-inventory-1/semantics": "VALUE_OBSERVED",
        "/demand": "COLLECTION_COMPLETE", "/demand/test-demand-1/day": "VALUE_OBSERVED",
        "/demand/test-demand-1/quantity": "VALUE_OBSERVED",
        "/demand/test-demand-1/semantics": "VALUE_OBSERVED",
        "/demand/test-demand-2/day": "VALUE_OBSERVED",
        "/demand/test-demand-2/quantity": "VALUE_OBSERVED",
        "/demand/test-demand-2/semantics": "VALUE_OBSERVED", "/supply": "COLLECTION_COMPLETE",
        "/supply/test-supply-1/supplyId": "VALUE_OBSERVED",
        "/supply/test-supply-1/remainingQty": "VALUE_OBSERVED",
        "/supply/test-supply-1/availableDate": "VALUE_OBSERVED",
        "/supply/test-supply-1/status": "VALUE_OBSERVED",
        "/policy/horizonDays": "RULE_VALUE", "/policy/bufferDays": "RULE_VALUE",
        "/policy/maxAgeHours": "RULE_VALUE", "/policy/moq": "RULE_VALUE",
        "/policy/orderMultiple": "RULE_VALUE", "/policy/candidateDates": "RULE_VALUE",
        "/policy/maxOrderQty": "RULE_VALUE", "/policy/otherConstraints": "RULE_VALUE",
        "/policy/qualityDisposition": "RULE_VALUE"}
    counts = {"/inventory": 1, "/demand": 2, "/supply": 1}
    provenance = []
    for path, assertion in paths.items():
        if admittable_shape:
            nature = "ERP_NETWORK" if path == "/mapping" else "CONTROLLED_FACT"
            extra = {} if nature == "ERP_NETWORK" else {
                "factBasis": "Offline contract-test value; not a real business fact."}
        else:
            nature = "SIMULATED"
            extra = {"testPurpose": "Admission contract test; no ERP observation occurred."}
        provenance.append(dict(fieldPath=path, assertion=assertion, nature=nature,
            sourceVersion="test-only-source-v1", owner="test-only-owner",
            sourceRef="offline-contract:admission-sample", observedAt=as_of,
            valueDigest=fingerprint(_field_value(payload, path)), recordCount=counts.get(path), **extra))
    content = RuleContent.model_validate(rules_content)
    return dict(packageVersion="s01-admission-package-v1",
        admissionMode="REAL_ANALYSIS" if admittable_shape else "ENGINEERING_TEST",
        evidenceLevel="TEST_ONLY_CONTRACT", inputId="test-only-input", fixtureId="test-only-input",
        assembledAt="2026-11-12T01:00:00Z", **deepcopy(payload), provenance=provenance,
        rules=dict(attestationKind="OPERATOR_PROVIDED_CONTROLLED_RECORD", ruleVersion=policy["version"],
            contentDigest=fingerprint(content.model_dump(mode="json")), content=rules_content,
            owner="test-only-rule-owner", approvedBy="test-only-approver",
            approvalRecordRef="offline-contract:not-a-business-approval", signedAt="2026-11-11T00:00:00Z",
            effectiveFrom="2026-11-01T00:00:00Z", effectiveUntil="2026-12-01T00:00:00Z"))


def build_teaching_admission_package() -> dict:
    """Return a server-shaped teaching package with sanitized artifact references."""

    base = build_test_only_admission_package(admittable_shape=True)
    base["packageVersion"] = "s01-teaching-admission-package-v1"
    base["admissionMode"] = "TEACHING_SIMULATION"
    base["sourceNature"] = "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"
    base.pop("evidenceLevel")
    base["inputId"] = base["fixtureId"] = "teaching-batch-input-1"
    base["policy"]["version"] = "teaching-s01-rules-v1"
    base["rules"]["content"]["policy"] = deepcopy(base["policy"])
    base["rules"] = {
        "ruleVersion": "teaching-s01-rules-v1",
        "contentDigest": fingerprint(base["rules"]["content"]),
        "content": base["rules"]["content"],
        "owner": "teaching-rule-owner",
        "recordRef": "trusted-artifact:teaching-rule-v1",
        "recordedAt": "2026-11-11T00:00:00Z",
        "effectiveFrom": "2026-11-01T00:00:00Z",
        "effectiveUntil": "2026-12-01T00:00:00Z",
    }
    read_back_manifest_ref = "trusted-artifact:erp-read-back-manifest-batch-1"
    read_back_ref = "trusted-artifact:erp-read-back-resource-batch-1"
    for item in base["provenance"]:
        item.pop("factBasis", None)
        if item["fieldPath"].startswith("/policy/"):
            item["nature"] = "CONTROLLED_TEACHING_RULE"
            item["sourceVersion"] = "teaching-s01-rules-v1"
            item["sourceRef"] = base["rules"]["recordRef"]
            item["teachingBasis"] = "Explicit teaching-only rule; no enterprise business signoff."
        else:
            item["nature"] = "ERP_NETWORK"
            item["sourceVersion"] = "teaching-erp-api-v1"
            item["sourceRef"] = read_back_ref
            item["observedAt"] = "2026-11-12T00:30:00Z"
        item["valueDigest"] = fingerprint(_field_value(base, item["fieldPath"]))
    record_ids = sorted(
        [row["recordId"] for row in base["inventory"]]
        + [row["recordId"] for row in base["demand"]]
        + [row["recordId"] for row in base["supply"]]
    )
    scope_digest = fingerprint(base["scope"])
    base["teachingBatch"] = {
        "batchId": "teaching-batch-1",
        "writeBatchId": "teaching-batch-1",
        "readBackBatchId": "teaching-batch-1",
        "writeOperationRef": "teaching-erp+https:operation/write/teaching-batch-1",
        "writeReceiptRef": "trusted-artifact:erp-write-receipt-batch-1",
        "writeReceiptDigest": "1" * 64,
        "writeArtifactDigest": "2" * 64,
        "writeCanonicalContentDigest": "0" * 64,
        "readBackOperationRef": "teaching-erp+https:operation/read/teaching-batch-1",
        "readBackArtifactRef": read_back_manifest_ref,
        "readBackArtifactDigest": "0" * 64,
        "readBackObservedAt": "2026-11-12T00:30:00Z",
        "readBackArtifacts": [{
            "alias": "canonical-s01-resources",
            "artifactRef": read_back_ref,
            "operationRef": "teaching-erp+https:operation/get/canonical-s01-resources",
            "rawResponseDigest": "4" * 64,
            "observedAt": "2026-11-12T00:30:00Z",
            "recordIds": record_ids,
            "contentDigest": fingerprint({
                "recordIds": record_ids,
                "fields": sorted(
                    ({"fieldPath": item["fieldPath"], "valueDigest": item["valueDigest"]}
                     for item in base["provenance"] if item["nature"] == "ERP_NETWORK"),
                    key=lambda item: item["fieldPath"],
                ),
            }),
        }],
        "writeScopeDigest": scope_digest,
        "readBackScopeDigest": scope_digest,
        "canonicalScopeDigest": scope_digest,
        "writeRecordIds": record_ids,
        "readBackRecordIds": record_ids,
        "readBackContentDigest": "0" * 64,
    }
    manifest = base["teachingBatch"]
    manifest["readBackArtifactDigest"] = fingerprint({
        "batchId": manifest["readBackBatchId"],
        "operationRef": manifest["readBackOperationRef"],
        "observedAt": manifest["readBackObservedAt"],
        "artifacts": sorted(manifest["readBackArtifacts"], key=lambda item: item["alias"]),
    })
    base["teachingBatch"]["readBackContentDigest"] = teaching_readback_content_digest(base)
    base["teachingBatch"]["writeCanonicalContentDigest"] = base["teachingBatch"]["readBackContentDigest"]
    return base


def hand_calculated_golden_case(*, opening, demand, supply, moq, order_multiple,
                                max_order_qty, candidate_day, quality="VERIFIED_CLEAR") -> dict:
    """Independent S01 arithmetic oracle including candidate constraints and arrival day."""

    required = [opening, moq, order_multiple, max_order_qty, candidate_day, *demand, *supply]
    if any(value is None for value in required):
        return {
            "status": "INSUFFICIENT_DATA",
            "baselineBalances": [],
            "gapQuantity": None,
            "firstStockoutDay": None,
            "candidateQuantity": None,
            "candidateBalances": [],
            "candidateFirstStockoutDay": None,
            "constraintOutcome": "DATA_QUALITY_BLOCKED",
        }
    numbers = {
        "opening": Decimal(str(opening)),
        "moq": Decimal(str(moq)),
        "orderMultiple": Decimal(str(order_multiple)),
        "maxOrderQty": Decimal(str(max_order_qty)),
    }
    demand_values = [Decimal(str(value)) for value in demand]
    supply_values = [Decimal(str(value)) for value in supply]
    if (
        len(demand_values) != len(supply_values)
        or not demand_values
        or candidate_day < 1
        or candidate_day > len(demand_values)
        or any(value < 0 for value in [*numbers.values(), *demand_values, *supply_values])
        or numbers["orderMultiple"] == 0
        or numbers["maxOrderQty"] == 0
    ):
        return {
            "status": "INSUFFICIENT_DATA",
            "baselineBalances": [],
            "gapQuantity": None,
            "firstStockoutDay": None,
            "candidateQuantity": None,
            "candidateBalances": [],
            "candidateFirstStockoutDay": None,
            "constraintOutcome": "DATA_QUALITY_BLOCKED",
        }

    def ledger(extra_quantity=Decimal(0)):
        balance = numbers["opening"]
        balances = []
        first = None
        for index, (incoming, outgoing) in enumerate(zip(supply_values, demand_values), start=1):
            if index == candidate_day:
                incoming += extra_quantity
            balance += incoming - outgoing
            balances.append(balance)
            if balance < 0 and first is None:
                first = index
        return balances, first

    baseline, first = ledger()
    gap = max(Decimal(0), sum(demand_values) - numbers["opening"] - sum(supply_values))
    result = {
        "status": "CALCULATED",
        "baselineBalances": [str(value) for value in baseline],
        "gapQuantity": str(gap),
        "firstStockoutDay": first,
        "candidateQuantity": None,
        "candidateBalances": [],
        "candidateFirstStockoutDay": None,
        "constraintOutcome": None,
    }
    if quality != "VERIFIED_CLEAR":
        result["constraintOutcome"] = "QUALITY_REQUIRES_RESOLUTION"
        return result
    if gap == 0:
        result["constraintOutcome"] = (
            "INTERMEDIATE_SHORTAGE_POLICY_UNDEFINED" if first is not None else "NO_REPLENISHMENT_NEEDED"
        )
        return result
    quantity = (
        max(gap, numbers["moq"]) / numbers["orderMultiple"]
    ).to_integral_value(rounding=ROUND_CEILING) * numbers["orderMultiple"]
    result["candidateQuantity"] = str(quantity)
    if quantity > numbers["maxOrderQty"]:
        result["constraintOutcome"] = "NO_FEASIBLE_QUANTITY"
        return result
    candidate, candidate_first = ledger(quantity)
    result["candidateBalances"] = [str(value) for value in candidate]
    result["candidateFirstStockoutDay"] = candidate_first
    result["constraintOutcome"] = (
        "CANDIDATE_STILL_HAS_INTERMEDIATE_SHORTAGE"
        if candidate_first is not None else "CANDIDATE_FEASIBLE"
    )
    return result


__all__ = [
    "build_teaching_admission_package",
    "build_test_only_admission_package",
    "hand_calculated_golden_case",
]
