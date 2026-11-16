"""Public O01 handler result; handlers never write orchestration tables."""
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DomainResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    contractVersion: Literal["0.1.0", "0.2.0"]
    sourceNature: Literal["SIMULATED_ENGINEERING", "TEACHING_ERP_OBSERVED", "SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP", "MIDDLEWARE_TEACHING_DATA"]
    completeness: Literal["RULES_ONLY", "PARTIAL", "BLOCKED"]
    scope: dict
    snapshotRef: str = Field(min_length=1, max_length=128)
    dataReport: dict
    analysisReport: dict
    sourceBundleRef: dict | None = None

    @model_validator(mode='after')
    def version_source(self):
        if self.sourceNature == 'MIDDLEWARE_TEACHING_DATA' and (self.contractVersion != '0.2.0' or not self.sourceBundleRef):
            raise ValueError('VERSIONED_TEACHING_SOURCE_REQUIRED')
        if self.contractVersion == '0.1.0' and self.sourceBundleRef is not None:
            raise ValueError('LEGACY_SOURCE_BUNDLE_UNSUPPORTED')
        return self


class ScenarioHandler(Protocol):
    def validate(self, parameters): ...
    def run(self, context, parameters) -> DomainResult | None: ...
