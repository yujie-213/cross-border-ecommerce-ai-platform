"""Offline deterministic provider, always explicitly assembled by caller/tests."""
from decimal import Decimal
import json
import threading
import time

from commerce_hub.capabilities.models.contracts import ProviderResult, ProviderRequest, Usage


def sample_output():
    item = {"text": "Synthetic facts require human review.", "supportRefs": ["fact-1"]}
    return dict(recommendationReasons=[item], keyEvidence=[item], majorRisks=[item], humanConfirmations=[])


class MockProvider:
    def __init__(self, *, mode="success", delay=0, entered=None, release=None):
        self.mode, self.delay = mode, delay
        self.entered, self.release = entered, release
        self.calls = 0
        self.requests = []
        self.lock = threading.Lock()

    def describe_capabilities(self):
        return frozenset({"structured_output"})

    def preflight(self, payload, cost):
        if payload["modelRevision"] != "mock-s01-v1":
            raise ValueError("UNSUPPORTED_MODEL")

    def invoke(self, request):
        request = ProviderRequest.model_validate(request.model_dump())
        with self.lock:
            self.calls += 1
            self.requests.append(request)
        if self.entered:
            self.entered.set()
        if self.release:
            self.release.wait(5)
        time.sleep(self.delay)
        if self.mode == "exception":
            raise RuntimeError("SENSITIVE_BODY_DO_NOT_LOG")
        output = sample_output()
        if self.mode == "missing":
            output.pop("majorRisks")
        if self.mode == "type":
            output["keyEvidence"] = "invalid-array"
        if self.mode == "extra":
            output["purchaseQuantity"] = 100
        statuses = {"refused": ("REFUSED", "refusal"), "truncated": ("TRUNCATED", "length"),
                    "timeout": ("TIMEOUT", "error"), "unavailable": ("UNAVAILABLE", "error"),
                    "rate_limit": ("RATE_LIMITED", "error"), "auth": ("AUTH_ERROR", "error")}
        status, finish = statuses.get(self.mode, ("COMPLETED", "stop"))
        unknown = self.mode in {"unknown", "timeout", "unavailable"}
        usage = Usage(inputTokens=None if unknown else 64, outputTokens=None if unknown else 32,
            actualCost=None if unknown else Decimal("0.0001"), currency="TEST", pricingVersion="mock-v1")
        return ProviderResult(status=status, finishReason=finish, content="{" if self.mode == "json" else json.dumps(output),
            actualModelRevision="different-model" if self.mode == "model_mismatch" else "mock-s01-v1", usage=usage)
