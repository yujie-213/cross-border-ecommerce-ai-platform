"""Executable subset of AI design v0.2 §9.1; exact logical names, no aliases."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.:-]+$")]
SnapshotIdentifier = Annotated[str, Field(strict=True, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class VersionedRef(StrictModel):
    id: Identifier
    version: Identifier

    @field_validator("version")
    @classmethod
    def immutable_version(cls, value):
        if value.lower() == "latest":
            raise ValueError("unversioned reference")
        return value


class DataRef(VersionedRef):
    tenantId: Identifier


class TaskRef(StrictModel):
    tenantId: Identifier
    taskId: Identifier


class QueryRef(StrictModel):
    tenantId: Identifier
    queryId: Identifier


class PrincipalRef(StrictModel):
    tenantId: Identifier
    principalId: Identifier


class ModelRequest(StrictModel):
    schemaVersion: Literal["0.2"]
    logicalCallId: Identifier
    attemptId: Identifier
    taskRef: TaskRef | None
    queryRef: QueryRef | None
    planVersion: Identifier | None
    participantId: Identifier | None
    snapshotId: SnapshotIdentifier | None
    principalRef: PrincipalRef
    policyContextRef: VersionedRef
    purpose: Identifier
    deploymentRef: VersionedRef
    promptRef: VersionedRef
    contextBundleRef: DataRef
    outputSchemaRef: VersionedRef
    requiredCapabilities: list[Literal["structured_output"]] = Field(max_length=1)
    toolSpecRefs: list[VersionedRef] = Field(max_length=0)
    parametersRef: VersionedRef
    allowanceRef: DataRef
    deadline: datetime
    cachePolicyRef: VersionedRef
    traceId: Identifier
    parentSpanId: Identifier

    @field_validator("deadline", mode="before")
    @classmethod
    def utc_deadline(cls, value):
        if isinstance(value, str):
            # A concrete RFC3339 timestamp is required, never a date or numeric epoch.
            if "T" not in value or not value.endswith(("Z", "+00:00")):
                raise ValueError("UTC timestamp required")
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset().total_seconds() != 0:
            raise ValueError("UTC timestamp required")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def bindings(self):
        if (self.taskRef is None) == (self.queryRef is None):
            raise ValueError("exactly one owner required")
        owner = self.taskRef or self.queryRef
        if any(ref.tenantId != owner.tenantId for ref in [self.principalRef, self.contextBundleRef, self.allowanceRef]):
            raise ValueError("tenant mismatch")
        if self.taskRef and not all([self.planVersion, self.participantId, self.snapshotId]):
            raise ValueError("domain binding required")
        if self.queryRef and (self.planVersion is not None or self.participantId is not None):
            raise ValueError("invalid query binding")
        return self


class Parameters(StrictModel):
    temperature: Literal[0] = 0
    maxOutputTokens: Annotated[int, Field(strict=True, ge=1, le=1024)]

    @field_validator("temperature", mode="before")
    @classmethod
    def strict_temperature(cls, value):
        if type(value) is not int or value != 0:
            raise ValueError("unsupported temperature")
        return value


class Message(StrictModel):
    role: Literal["system", "user"]
    content: str = Field(strict=True, min_length=1, max_length=16384)


class ProviderPayload(StrictModel):
    modelRevision: Identifier
    messages: list[Message] = Field(min_length=2, max_length=2)
    parameters: Parameters
    outputSchema: dict
    toolSpecs: list = Field(max_length=0)


class ProviderControl(ModelRequest):
    timeoutMs: Annotated[int, Field(strict=True, ge=1, le=30000)]
    digests: dict[str, str]


class ProviderRequest(StrictModel):
    payload: ProviderPayload
    control: ProviderControl

    @model_validator(mode="after")
    def resolved_payload(self):
        fields = {"resolvedPromptDigest": self.payload.model_dump()["messages"],
            "parametersDigest": self.payload.parameters.model_dump(), "outputSchemaDigest": self.payload.outputSchema,
            "toolSpecsDigest": self.payload.toolSpecs}
        if set(self.control.digests) != set(fields) | {"contextDigest", "promptContentHash"}:
            raise ValueError("incomplete digests")
        for key, value in self.control.digests.items():
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("invalid digest")
        for key, value in fields.items():
            expected = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            if self.control.digests[key] != expected:
                raise ValueError("payload digest mismatch")
        if [m.role for m in self.payload.messages] != ["system", "user"]:
            raise ValueError("invalid message roles")
        return self


class Usage(StrictModel):
    inputTokens: Annotated[int, Field(strict=True, ge=0, le=2147483647)] | None = None
    outputTokens: Annotated[int, Field(strict=True, ge=0, le=2147483647)] | None = None
    cachedInputTokens: Annotated[int, Field(strict=True, ge=0, le=2147483647)] | None = None
    uncachedInputTokens: Annotated[int, Field(strict=True, ge=0, le=2147483647)] | None = None
    actualCost: Decimal | None = None
    currency: Literal["TEST", "USD"]
    pricingVersion: Identifier

    @field_validator("actualCost")
    @classmethod
    def valid_cost(cls, value):
        if value is not None and (not value.is_finite() or value < 0 or value != value.quantize(Decimal("0.00000001"))):
            raise ValueError("invalid cost")
        return value


class ProviderResult(StrictModel):
    status: Literal["COMPLETED", "REFUSED", "TRUNCATED", "TIMEOUT", "RATE_LIMITED", "AUTH_ERROR", "UNAVAILABLE", "PROVIDER_ERROR"]
    content: str | None = Field(default=None, max_length=65536, repr=False)
    finishReason: Literal["stop", "length", "refusal", "error"]
    actualModelRevision: Identifier | None = None
    # Never log raw remote IDs; adapter supplies a SHA256 fingerprint only.
    providerRequestId: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    usage: Usage


class ModelResponse(StrictModel):
    status: Literal["SUCCESS", "TECH_ERROR"]
    code: Identifier
    validatedObject: dict | None = Field(default=None, repr=False)
    usageRef: str | None = None
    auditRef: str | None = None
    usageStatus: Literal["KNOWN", "UNKNOWN", "NOT_SENT"]
    finishReason: str | None = None
    actualModelRevision: str | None = None
    versionBundle: dict = Field(default_factory=dict)
    cacheStatus: Literal["OFF"] = "OFF"
    toolRequests: list = Field(default_factory=list, max_length=0)


class ModelProvider(Protocol):
    def describe_capabilities(self) -> frozenset[str]: ...
    def preflight(self, payload: dict, cost: Decimal) -> None: ...
    def invoke(self, request: ProviderRequest) -> ProviderResult: ...
