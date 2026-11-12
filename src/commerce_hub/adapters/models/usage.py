"""Provider protocol mapping into the stable, optional usage dimensions."""
from commerce_hub.capabilities.models.contracts import Usage


def chat_usage(value):
    """Map documented chat counters; absent dimensions stay unknown.

    Input plus output may determine total; no missing component or cache count
    is inferred as zero. Contradictory provider counters fail validation.
    """
    if not isinstance(value, dict):
        value = {}
    return Usage(inputTokens=value.get("prompt_tokens"), outputTokens=value.get("completion_tokens"),
        totalTokens=value.get("total_tokens"), cachedInputTokens=value.get("prompt_cache_hit_tokens"),
        uncachedInputTokens=value.get("prompt_cache_miss_tokens"))


def ollama_usage(value):
    """Local generation counters have no implied bill or cache measurement."""
    if not isinstance(value, dict):
        value = {}
    return Usage(inputTokens=value.get("prompt_eval_count"), outputTokens=value.get("eval_count"))
