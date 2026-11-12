import pytest
from pydantic import ValidationError

from commerce_hub.adapters.models.usage import chat_usage, ollama_usage
from commerce_hub.capabilities.models.contracts import Usage


@pytest.mark.parametrize("raw,expected", [
    ({}, (None, None, None)),
    ({"prompt_tokens": 12}, (12, None, None)),
    ({"completion_tokens": 3, "total_tokens": 15}, (None, 3, 15)),
    ({"prompt_tokens": 12, "completion_tokens": 3}, (12, 3, 15)),
    ({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, (0, 0, 0)),
])
def test_provider_missing_dimensions_are_unknown(raw, expected):
    usage = chat_usage(raw)
    assert (usage.inputTokens, usage.outputTokens, usage.totalTokens) == expected
    assert usage.actualCost is usage.currency is usage.pricingVersion is None
    assert usage.cachedInputTokens is None


@pytest.mark.parametrize("raw", [
    {"prompt_tokens": True}, {"completion_tokens": -1},
    {"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 20},
    {"prompt_tokens": 12, "prompt_cache_hit_tokens": 13},
    {"total_tokens": 100, "prompt_cache_hit_tokens": 60, "prompt_cache_miss_tokens": 60},
])
def test_invalid_provider_usage_is_rejected(raw):
    with pytest.raises(ValidationError):
        chat_usage(raw)


def test_provider_neutral_usage_supports_local_models_without_currency():
    usage = Usage(inputTokens=10, outputTokens=5)
    assert usage.totalTokens == 15 and usage.actualCost is None
    assert Usage(inputTokens=10, outputTokens=5, actualCost="0", currency="USD").actualCost == 0
    assert ollama_usage(dict(prompt_eval_count=10, eval_count=5)) == usage
    assert ollama_usage(dict(prompt_eval_count=10)).outputTokens is None
