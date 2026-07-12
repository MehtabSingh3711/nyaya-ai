import pytest
from nyaya_ai.llm.cascade import _DISABLED_TIERS

@pytest.fixture(autouse=True)
def clear_circuit_breaker():
    """Clear the LLM cascade circuit breaker state between tests."""
    _DISABLED_TIERS.clear()
