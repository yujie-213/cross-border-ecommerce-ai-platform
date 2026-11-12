"""Official DeepSeek HTTP adapter, documented JSON Output, no SDK/redirect/proxy/retry."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING
import hashlib
import http.client
import json
import socket
import ssl
import threading

from pydantic import ValidationError

from commerce_hub.capabilities.models.contracts import ProviderRequest, ProviderResult, Usage


@dataclass(frozen=True)
class ConnectivityAuthorization:
    authorization_id: str
    max_cost_usd: Decimal


class DeepSeekProvider:
    """Only explicit synthetic connectivity assembly receives an authorization object.

    Official response supplies token counts, not a billed USD amount. Never settle an estimate.
    Rates below are a conservative send-admission ceiling, not G02 actual-cost facts.
    """
    def __init__(self, settings, *, authorization=None, connection_factory=None):
        self.settings, self.authorization = settings, authorization
        self.connection_factory = connection_factory or http.client.HTTPSConnection
        self._used = False
        self._lock = threading.Lock()

    def describe_capabilities(self):
        # Documented JSON Output plus LOCAL Schema validation, not native strict JSON Schema.
        return frozenset({"structured_output"})

    @staticmethod
    def cost_upper(payload):
        input_upper = sum(len(m["content"].encode()) for m in payload["messages"]) + 4096
        return ((Decimal(input_upper) * Decimal("0.00000030")) +
                Decimal(payload["parameters"]["maxOutputTokens"]) * Decimal("0.00000120")).quantize(
                    Decimal("0.00000001"), rounding=ROUND_CEILING)

    def preflight(self, payload, cost):
        auth = self.authorization
        if (not self.settings.model_network_enabled or self.settings.model_provider != "deepseek" or
            auth is None or not auth.authorization_id):
            raise ValueError("NETWORK_DISABLED")
        if not self.settings.model_api_key.get_secret_value():
            raise ValueError("CREDENTIAL_MISSING")
        if (payload["modelRevision"] != "deepseek-flash" or self.settings.model_name != "deepseek-flash" or
            self.settings.model_base_url != "https://api.deepseek.com" or
            payload["parameters"]["maxOutputTokens"] > min(self.settings.model_max_output_tokens, 128)):
            raise ValueError("UNSUPPORTED_MODEL")
        if (not auth.max_cost_usd.is_finite() or not Decimal("0") < auth.max_cost_usd <= Decimal("1") or
            self.cost_upper(payload) > min(cost, auth.max_cost_usd)):
            raise ValueError("COST_ALLOWANCE_TOO_SMALL")

    def invoke(self, request):
        request = ProviderRequest.model_validate(request.model_dump())
        payload = request.payload.model_dump()
        self.preflight(payload, self.authorization.max_cost_usd if self.authorization else Decimal("0"))
        with self._lock:
            if self._used:
                raise ValueError("NETWORK_DISABLED")
            self._used = True  # At most one transport attempt per explicit authorization/instance.
        body = json.dumps(dict(model=payload["modelRevision"], messages=payload["messages"],
            temperature=0, max_tokens=payload["parameters"]["maxOutputTokens"],
            thinking={"type": "disabled"}, response_format={"type": "json_object"}, stream=False), ensure_ascii=False).encode()
        conn = None
        unknown = Usage(currency="USD", pricingVersion="deepseek-cost-unreconciled-v1")
        def failure(code):
            return ProviderResult(status=code, finishReason="error", usage=unknown)
        try:
            # HTTPSConnection never follows redirects or reads environment proxy settings. TLS verification stays on.
            conn = self.connection_factory("api.deepseek.com", timeout=request.control.timeoutMs/1000,
                context=ssl.create_default_context())
            conn.request("POST", "/chat/completions", body=body, headers={"Content-Type": "application/json",
                "Authorization": "Bearer " + self.settings.model_api_key.get_secret_value()})
            response = conn.getresponse()
            if response.status != 200:
                return failure("AUTH_ERROR" if response.status in {401, 402, 403} else
                    "RATE_LIMITED" if response.status == 429 else "UNAVAILABLE" if response.status >= 500 else "PROVIDER_ERROR")
            raw = response.read(65537)
            if len(raw) > 65536:
                return ProviderResult(status="TRUNCATED", finishReason="length", usage=unknown)
            data = json.loads(raw)
            usage = data.get("usage") or {}
            # All applicable counts must be explicit and consistent; no default zero.
            inp, out = usage.get("prompt_tokens"), usage.get("completion_tokens")
            if (type(inp) is not int or type(out) is not int or inp < 0 or out < 0 or
                usage.get("total_tokens") != inp+out):
                inp = out = None
            actual = Usage(inputTokens=inp, outputTokens=out, actualCost=None, currency="USD",
                cachedInputTokens=usage.get("prompt_cache_hit_tokens"), uncachedInputTokens=usage.get("prompt_cache_miss_tokens"),
                pricingVersion="deepseek-cost-unreconciled-v1")
            choices = data["choices"]
            if len(choices) != 1:
                return failure("PROVIDER_ERROR")
            choice = choices[0]
            message, finish = choice["message"], choice["finish_reason"]
            refused = bool(message.get("refusal")) or finish == "content_filter"
            status = "REFUSED" if refused else "TRUNCATED" if finish == "length" else "COMPLETED" if finish == "stop" else "PROVIDER_ERROR"
            if message.get("tool_calls"):
                status = "PROVIDER_ERROR"  # No tools in this deployment.
            return ProviderResult(status=status, finishReason="refusal" if refused else "length" if finish == "length" else
                "stop" if status == "COMPLETED" else "error", content=message.get("content"), actualModelRevision=data["model"],
                providerRequestId=hashlib.sha256(str(data["id"]).encode()).hexdigest(), usage=actual)
        except (TimeoutError, socket.timeout):
            return failure("TIMEOUT")
        except (OSError, ValueError, KeyError, TypeError, IndexError, ValidationError):
            return failure("PROVIDER_ERROR")
        finally:
            if conn:
                conn.close()
