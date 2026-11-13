"""Bounded, additive S01 engineering contracts; no production defaults."""
from datetime import date, timezone
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, AwareDatetime, AfterValidator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


Quantity = Annotated[Decimal, Field(max_digits=20, decimal_places=8, allow_inf_nan=False)]
CanonicalQuantity = Annotated[Decimal, Field(max_digits=40, decimal_places=16, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")]
UtcTimestamp = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(timezone.utc))]


class Mapping(Contract):
    version: Identifier
    sourceSku: Identifier
    sourceStore: Identifier
    sourceWarehouse: Identifier
    canonicalSkuId: Identifier
    storeId: Identifier
    warehouseId: Identifier
    sourceUnit: Literal["EA", "CASE"]
    unit: Literal["EA"]
    unitsPerSourceUnit: Annotated[Quantity, Field(gt=0)]


class Inventory(Contract):
    recordId: Identifier
    sku: Identifier
    store: Identifier
    warehouse: Identifier
    unit: Literal["EA", "CASE"]
    availableQty: Quantity | None
    reservedQty: Quantity | None = None
    semantics: Literal["NET_AVAILABLE"]
    sourceUpdatedAt: UtcTimestamp


class Demand(Contract):
    recordId: Identifier
    sku: Identifier
    store: Identifier
    warehouse: Identifier
    unit: Literal["EA", "CASE"]
    day: date
    quantity: Quantity | None
    semantics: Literal["INCREMENTAL_EXCLUDES_RESERVED"]


class Supply(Contract):
    recordId: Identifier
    supplyId: Identifier
    sku: Identifier
    store: Identifier
    warehouse: Identifier
    unit: Literal["EA", "CASE"]
    remainingQty: Quantity | None
    availableDate: date | None
    status: Literal["OPEN", "RECEIVED", "CANCELLED", "UNKNOWN"]


class Policy(Contract):
    version: Literal["engineering-demo-v1"]
    horizonDays: int = Field(ge=1, le=31, strict=True)
    bufferDays: int = Field(ge=0, le=14, strict=True)
    maxAgeHours: int = Field(ge=1, le=168, strict=True)
    moq: Quantity | None
    orderMultiple: Quantity | None
    candidateDates: tuple[date, ...] = Field(max_length=5)
    maxOrderQty: Quantity | None
    # All other purchasing constraints are explicitly outside this sample policy.
    otherConstraints: Literal["ENGINEERING_NOT_APPLICABLE"]
    qualityDisposition: Literal["SAMPLE_CLEAR", "INVESTIGATE", "UNKNOWN"]


class FixtureInput(Contract):
    sourceNature: Literal["SIMULATED_ENGINEERING"]
    fixtureId: Identifier
    asOf: UtcTimestamp
    coverageComplete: bool = Field(strict=True)
    mapping: Mapping
    inventory: tuple[Inventory, ...] = Field(max_length=4)
    demand: tuple[Demand, ...] = Field(max_length=45)
    supply: tuple[Supply, ...] = Field(max_length=30)
    policy: Policy


class AdmittedPolicy(Policy):
    """Explicitly reviewed business semantics; never inferred from a fixture."""
    version: Identifier
    otherConstraints: Literal["REVIEWED_NOT_APPLICABLE", "UNCONFIRMED"]
    qualityDisposition: Literal["VERIFIED_CLEAR", "INVESTIGATE", "UNKNOWN"]
    advisoryOnly: bool = Field(default=False, strict=True, exclude_if=lambda value: not value)


class AdmittedInput(Contract):
    sourceNature: Literal["TEACHING_ERP_OBSERVED", "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP"]
    # Retain the common input identifier for existing projection consumers.
    fixtureId: Identifier
    provenanceRef: Identifier
    rulesRef: Identifier
    asOf: UtcTimestamp
    businessDate: date | None = Field(default=None, exclude_if=lambda value: value is None)
    coverageComplete: bool = Field(strict=True)
    mapping: Mapping
    inventory: tuple[Inventory, ...] = Field(max_length=4)
    demand: tuple[Demand, ...] = Field(max_length=45)
    supply: tuple[Supply, ...] = Field(max_length=30)
    policy: AdmittedPolicy


class Issue(Contract):
    code: str
    severity: Literal["BLOCK", "WARN", "INFO"]
    path: str
    affects: Literal["CALCULATION", "CANDIDATES", "PROVENANCE"]


class CanonicalInventory(Inventory):
    availableQty: CanonicalQuantity | None
    reservedQty: CanonicalQuantity | None = None


class CanonicalDemand(Demand):
    quantity: CanonicalQuantity | None


class CanonicalSupply(Supply):
    remainingQty: CanonicalQuantity | None


class Projection(Contract):
    projectionVersion: Literal["s01-projection-v1"] = "s01-projection-v1"
    revision: str
    sourceBatchId: str
    input: FixtureInput | AdmittedInput
    inventory: tuple[CanonicalInventory, ...]
    demand: tuple[CanonicalDemand, ...]
    supply: tuple[CanonicalSupply, ...]
    issues: tuple[Issue, ...]


def fingerprint(value) -> str:
    import hashlib
    import json
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
