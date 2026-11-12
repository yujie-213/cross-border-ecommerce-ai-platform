"""D02: safe, non-calculable projection of observed teaching source facts."""
from typing import Literal, Annotated
from pydantic import Field, model_validator
from commerce_hub.data.contracts import Contract, fingerprint, UtcTimestamp

class Measurement(Contract):
    field: Literal["physical", "available", "moq", "carton_quantity", "lead_days", "quote_moq"]
    value: Annotated[str, Field(pattern=r"^-?[0-9]+(?:\.[0-9]+)?$", max_length=64)] | None
    unit: Literal["SOURCE_PIECE", "DAYS", "UNKNOWN"]

class ObservedDomain(Contract):
    domain: Literal["identity", "inventory", "demand", "supply", "availability", "moq", "orderMultiple", "quality"]
    state: Literal["OBSERVED", "MISSING", "INCOMPLETE", "ERROR"]
    measurements: tuple[Measurement, ...] = Field(default=(), max_length=20)
    sourceTimes: tuple[Annotated[str, Field(max_length=64, pattern=r"^[0-9TZ:+. \-]+$")], ...] = Field(default=(), max_length=20)
    sourceRefs: tuple[Annotated[str, Field(pattern=r"^read-[0-9a-f]{64}$")], ...] = Field(max_length=20)

class ObservationProjection(Contract):
    version: Literal["s01-teaching-observation-v1"] = "s01-teaching-observation-v1"
    sourceNature: Literal["TEACHING_ERP_OBSERVED"] = "TEACHING_ERP_OBSERVED"
    sourceSynthetic: bool = Field(strict=True)
    ownerConfirmed: bool = Field(strict=True)
    revalidationFailed: bool = Field(default=False, strict=True)
    scope: dict
    observedAt: UtcTimestamp
    domains: tuple[ObservedDomain, ...] = Field(min_length=8, max_length=8)
    revision: str

    @model_validator(mode="after")
    def bounded_scope(self):
        dimensions = {"canonicalSkuIds", "storeIds", "warehouseIds"}
        if (set(self.scope) != dimensions | {"tenantId", "fields"}
            or not isinstance(self.scope["tenantId"],str) or not 1 <= len(self.scope["tenantId"]) <= 64
            or self.scope["fields"] != ["quantity"]
            or any(not isinstance(self.scope[d],list) or len(self.scope[d])!=1
                or not isinstance(self.scope[d][0],str) or not 1 <= len(self.scope[d][0])<=128
                or "*" in self.scope[d][0] for d in dimensions)):
            raise ValueError("TEACHING_SINGLE_SKU_SCOPE_REQUIRED")
        return self


def project_observations(value):
    projection = ObservationProjection.model_validate(dict(value, revision=""))
    if len({d.domain for d in projection.domains}) != 8:
        raise ValueError("OBSERVED_DOMAINS_INCOMPLETE")
    body = projection.model_dump(mode="json", exclude={"revision"})
    return projection.model_copy(update={"revision": fingerprint(body)})


def verify_observations(value):
    projection = ObservationProjection.model_validate(value)
    rebuilt = project_observations(projection.model_dump(mode="json", exclude={"revision"}))
    if rebuilt.revision != projection.revision:
        raise ValueError("OBSERVED_PROJECTION_REVISION_MISMATCH")
    return projection
