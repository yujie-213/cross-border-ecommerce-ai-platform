"""The new Handler is available only through explicit offline engineering composition."""
from types import SimpleNamespace

import pytest

from commerce_hub.bootstrap.s01_business import registry


@pytest.mark.parametrize("environment,provider,network", [
    ("development", "mock", False), ("test", "deepseek", False), ("test", "mock", True)])
def test_live_or_network_composition_is_rejected(environment, provider, network):
    config = SimpleNamespace(environment=environment, model_provider=provider,
        model_network_enabled=network, model_timeout_seconds=15)
    with pytest.raises(ValueError, match="OFFLINE_MOCK"):
        registry(config)


def test_explicit_test_composition_keeps_one_original_task_budget():
    config = SimpleNamespace(environment="test", model_provider="mock",
        model_network_enabled=False, model_timeout_seconds=15)
    values = registry(config)
    assert list(values) == ["ENGINEERING_S01_BUSINESS"]
    spec = values["ENGINEERING_S01_BUSINESS"]
    assert spec.max_calls == 1 and spec.max_tokens == 24000 and str(spec.max_cost) == "0.01"
    assert spec.policy_version == "s01-business-mock-v1"
