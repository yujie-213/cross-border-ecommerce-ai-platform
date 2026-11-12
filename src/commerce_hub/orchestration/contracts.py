"""Public O01 handler result; handlers never write orchestration tables."""
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class DomainResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    contractVersion: Literal["0.1.0"]
    sourceNature: Literal["SIMULATED_ENGINEERING"]
    completeness: Literal["RULES_ONLY", "PARTIAL", "BLOCKED"]
    scope: dict
    snapshotRef: str = Field(min_length=1, max_length=128)
    dataReport: dict
    analysisReport: dict


class ScenarioHandler(Protocol):
    def validate(self, parameters): ...
    def run(self, context, parameters) -> DomainResult | None: ...
