"""Component tests: MockLLM behavior + fault injection isolation."""
import pytest
from scaffold.mock_llm import MockLLM, STUB_RESPONSES
from scaffold.mock_apis import (
    FaultInjector,
    MockColorsClient,
    SimulatedBadRequest,
    SimulatedServerError,
    SimulatedTimeout,
    SimulatedAuthError,
)


pytestmark = pytest.mark.component


# === MockLLM ==========================================================

async def test_mock_llm_returns_deterministic_decision():
    llm = MockLLM()
    result = await llm.first_call("describe red", "fetch_red")
    assert result["target_api"] == "colors"
    assert result["params"] == {"name": "red"}


async def test_mock_llm_unknown_scenario_raises():
    llm = MockLLM()
    with pytest.raises(KeyError):
        await llm.first_call("anything", "nonexistent_scenario")


async def test_mock_llm_second_call_returns_message():
    llm = MockLLM()
    msg = await llm.second_call(
        scenario="fetch_red", behavior="successful",
        api_response={"hex": "#FF0000"}, api_error=None,
    )
    assert "red" in msg.lower()
    assert "#FF0000" in msg


async def test_mock_llm_second_call_falls_back_for_missing_key():
    llm = MockLLM()
    msg = await llm.second_call(
        scenario="unknown", behavior="something_weird",
        api_response=None, api_error="SomeError",
    )
    # Falls back to a generic message; not empty.
    assert msg


# === FaultInjector (separated from production interface) ============

async def test_production_client_has_no_behavior_argument():
    """MockColorsClient.call takes only params, never behavior."""
    client = MockColorsClient()
    import inspect
    sig = inspect.signature(client.call)
    assert "behavior" not in sig.parameters


async def test_fault_injector_passes_through_on_success():
    inner = MockColorsClient()
    injector = FaultInjector(inner)
    result = await injector.call({"name": "red"}, behavior="successful")
    assert result["name"] == "red"


async def test_fault_injector_simulates_400():
    inner = MockColorsClient()
    injector = FaultInjector(inner)
    with pytest.raises(SimulatedBadRequest):
        await injector.call({}, behavior="api_400")


async def test_fault_injector_simulates_500():
    inner = MockColorsClient()
    injector = FaultInjector(inner)
    with pytest.raises(SimulatedServerError):
        await injector.call({}, behavior="api_500")


async def test_fault_injector_simulates_timeout():
    inner = MockColorsClient()
    injector = FaultInjector(inner)
    with pytest.raises(SimulatedTimeout):
        await injector.call({}, behavior="timeout")


async def test_fault_injector_simulates_auth_error():
    inner = MockColorsClient()
    injector = FaultInjector(inner)
    with pytest.raises(SimulatedAuthError):
        await injector.call({}, behavior="api_401_403")


async def test_fault_injector_returns_none_for_not_found():
    inner = MockColorsClient()
    injector = FaultInjector(inner)
    assert await injector.call({}, behavior="not_found") is None


async def test_fault_injector_returns_empty_for_empty():
    inner = MockColorsClient()
    injector = FaultInjector(inner)
    assert await injector.call({}, behavior="empty") == {}


async def test_fault_injector_returns_partial_for_missing_field():
    inner = MockColorsClient()
    injector = FaultInjector(inner)
    result = await injector.call({}, behavior="missing_field")
    assert "name" in result  # subset of fields


async def test_fault_injector_returns_malformed_payload():
    inner = MockColorsClient()
    injector = FaultInjector(inner)
    result = await injector.call({}, behavior="malformed_payload")
    assert result.get("_malformed") is True