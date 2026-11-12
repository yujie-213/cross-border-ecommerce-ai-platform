"""Bounded DeepSeek adapter used only by the S01 model-evaluation tool.

It intentionally does not replace the accepted connectivity provider.  Official
responses contain token counts but no billed USD amount, so G02 actualCost stays
UNKNOWN. Dated authorization arithmetic belongs only in the evaluation evidence.
"""
from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
import http.client
import json
import socket
import ssl
import threading

from pydantic import ValidationError

from commerce_hub.adapters.models.usage import chat_usage
from commerce_hub.capabilities.models.contracts import ProviderRequest, ProviderResult, Usage


MODEL_REVISION = "deepseek-flash"


@dataclass(frozen=True)
class EvaluationAuthorization:
    authorization_id: str
    max_requests: int
    max_total_cost_usd: Decimal
    per_request_risk_usd: Decimal = Decimal("0.05")

    def __post_init__(self):
        if not self.authorization_id or not 1 <= len(self.authorization_id) <= 48:
            raise ValueError("INVALID_EVALUATION_AUTHORIZATION")
        if type(self.max_requests) is not int or not 1 <= self.max_requests <= 10:
            raise ValueError("INVALID_EVALUATION_REQUEST_LIMIT")
        if (not self.max_total_cost_usd.is_finite() or
                not Decimal("0") < self.max_total_cost_usd <= Decimal("1")):
            raise ValueError("INVALID_EVALUATION_COST_LIMIT")
        if (not self.per_request_risk_usd.is_finite() or
                not Decimal("0") < self.per_request_risk_usd <= self.max_total_cost_usd or
                self.per_request_risk_usd * self.max_requests > self.max_total_cost_usd):
            raise ValueError("INVALID_EVALUATION_RISK_RESERVATION")


@dataclass(frozen=True)
class EvaluationExchange:
    logical_call_id: str
    status: str
    model_revision: str | None
    input_tokens: int | None
    output_tokens: int | None
    cached_input_tokens: int | None
    uncached_input_tokens: int | None
    provider_request_fingerprint: str | None
    content: str | None = field(default=None, repr=False)


class EvaluationProvider:
    """Official-protocol, no-proxy/no-redirect/no-retry S01 evaluation provider."""

    def __init__(self, settings, *, authorization, connection_factory=None):
        self.settings = settings
        self.authorization = authorization
        self.connection_factory = connection_factory or http.client.HTTPSConnection
        self._lock = threading.Lock()
        self._logical_calls = set()
        self._reserved_exposure = Decimal("0")
        self._exchanges = {}

    def describe_capabilities(self):
        # DeepSeek JSON Output plus local schema/domain validation.
        return frozenset({"structured_output"})

    def risk_reservation(self, payload):
        """Explicit authorization exposure; admission never depends on a price formula."""
        if payload["parameters"]["maxOutputTokens"] > 1024:
            raise ValueError("UNSUPPORTED_MODEL")
        return self.authorization.per_request_risk_usd

    def preflight(self, payload, cost):
        auth = self.authorization
        if (not self.settings.model_network_enabled or self.settings.model_provider != "deepseek" or
                auth is None):
            raise ValueError("NETWORK_DISABLED")
        if not self.settings.model_api_key.get_secret_value():
            raise ValueError("CREDENTIAL_MISSING")
        if (payload["modelRevision"] != MODEL_REVISION or self.settings.model_name != MODEL_REVISION or
                self.settings.model_base_url != "https://api.deepseek.com" or
                payload["parameters"]["maxOutputTokens"] > min(self.settings.model_max_output_tokens, 1024)):
            raise ValueError("UNSUPPORTED_MODEL")
        risk = self.risk_reservation(payload)
        if risk > cost or risk > auth.max_total_cost_usd:
            raise ValueError("COST_ALLOWANCE_TOO_SMALL")

    def exchange(self, logical_call_id):
        """Return this-process evidence; callers must keep raw content in private storage."""
        with self._lock:
            return self._exchanges.get(logical_call_id)

    def invoke(self, request):
        request = ProviderRequest.model_validate(request.model_dump())
        payload = request.payload.model_dump()
        risk = self.risk_reservation(payload)
        self.preflight(payload, self.authorization.max_total_cost_usd)
        logical_call_id = request.control.logicalCallId
        with self._lock:
            if logical_call_id in self._logical_calls:
                raise ValueError("USAGE_MUST_BE_RECONCILED")
            if len(self._logical_calls) + 1 > self.authorization.max_requests:
                raise ValueError("BUDGET_DENIED")
            if self._reserved_exposure + risk > self.authorization.max_total_cost_usd:
                raise ValueError("BUDGET_DENIED")
            self._logical_calls.add(logical_call_id)
            self._reserved_exposure += risk

        body = json.dumps(
            dict(
                model=payload["modelRevision"],
                messages=payload["messages"],
                temperature=0,
                max_tokens=payload["parameters"]["maxOutputTokens"],
                thinking={"type": "disabled"},
                response_format={"type": "json_object"},
                stream=False,
            ),
            ensure_ascii=False,
        ).encode()
        conn = None
        unknown = Usage()

        def failure(code):
            exchange = EvaluationExchange(
                logical_call_id, code, None, None, None, None, None, None, None,
            )
            with self._lock:
                self._exchanges[logical_call_id] = exchange
            return ProviderResult(status=code, finishReason="error", usage=unknown)

        try:
            # HTTPSConnection neither follows redirects nor reads environment proxy settings.
            conn = self.connection_factory(
                "api.deepseek.com",
                timeout=request.control.timeoutMs / 1000,
                context=ssl.create_default_context(),
            )
            conn.request(
                "POST",
                "/chat/completions",
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + self.settings.model_api_key.get_secret_value(),
                },
            )
            response = conn.getresponse()
            if response.status != 200:
                return failure(
                    "AUTH_ERROR" if response.status in {401, 402, 403} else
                    "RATE_LIMITED" if response.status == 429 else
                    "UNAVAILABLE" if response.status >= 500 else "PROVIDER_ERROR"
                )
            raw = response.read(65537)
            if len(raw) > 65536:
                return failure("TRUNCATED")
            data = json.loads(raw)
            actual = chat_usage(data.get("usage"))
            choices = data["choices"]
            if len(choices) != 1:
                return failure("PROVIDER_ERROR")
            choice = choices[0]
            message = choice["message"]
            finish = choice["finish_reason"]
            refused = bool(message.get("refusal")) or finish == "content_filter"
            status = (
                "REFUSED" if refused else "TRUNCATED" if finish == "length" else
                "COMPLETED" if finish == "stop" else "PROVIDER_ERROR"
            )
            if message.get("tool_calls"):
                status = "PROVIDER_ERROR"
            request_fingerprint = hashlib.sha256(str(data["id"]).encode()).hexdigest()
            exchange = EvaluationExchange(
                logical_call_id=logical_call_id,
                status=status,
                model_revision=data.get("model"),
                input_tokens=actual.inputTokens,
                output_tokens=actual.outputTokens,
                cached_input_tokens=actual.cachedInputTokens,
                uncached_input_tokens=actual.uncachedInputTokens,
                provider_request_fingerprint=request_fingerprint,
                content=message.get("content"),
            )
            with self._lock:
                self._exchanges[logical_call_id] = exchange
            return ProviderResult(
                status=status,
                finishReason="refusal" if refused else "length" if finish == "length" else
                    "stop" if status == "COMPLETED" else "error",
                content=message.get("content"),
                actualModelRevision=data.get("model"),
                providerRequestId=request_fingerprint,
                usage=actual,
            )
        except (TimeoutError, socket.timeout):
            return failure("TIMEOUT")
        except (OSError, ValueError, KeyError, TypeError, IndexError, ValidationError, json.JSONDecodeError):
            return failure("PROVIDER_ERROR")
        finally:
            if conn:
                conn.close()
