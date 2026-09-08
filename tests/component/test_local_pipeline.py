"""Component tests: LocalMockSystem end-to-end pipeline."""
import pytest
from scaffold.mock_system import LocalMockSystem
from scaffold.models import ExecutionResult


pytestmark = pytest.mark.component


async def test_local_system_returns_execution_result():
    system = LocalMockSystem()
    result = await system.invoke("describe red", scenario="fetch_red")
    assert isinstance(result, ExecutionResult)
    assert result.response_text
    assert result.target_api == "colors"


async def test_local_system_handles_not_found():
    system = LocalMockSystem()
    result = await system.invoke("look up xyz", scenario="fetch_red_not_found", behavior="not_found")
    assert result.api_response is None
    assert result.target_api == "colors"  # the API was still called
    assert result.api_error is None  # not_found is not an exception
    assert "not found" in result.response_text.lower()


async def test_local_system_handles_api_500():
    system = LocalMockSystem()
    result = await system.invoke("describe red", scenario="fetch_red_api_500", behavior="api_500")
    assert result.api_error is not None
    assert result.api_error_category == "server_error"
    assert result.target_api is None


async def test_local_system_handles_timeout():
    system = LocalMockSystem()
    result = await system.invoke("describe red", scenario="fetch_red_timeout", behavior="timeout")
    assert result.api_error_category == "timeout"


async def test_local_system_handles_unknown_target_api():
    system = LocalMockSystem()
    # Build a synthetic scenario pointing at a non-existent API.
    from scaffold.mock_llm import STUB_RESPONSES
    STUB_RESPONSES["test_bad_target"] = {
        "action": "fetch", "target_api": "nonexistent_api",
        "params": {}, "reasoning": "test",
    }
    result = await system.invoke("x", scenario="test_bad_target")
    assert result.api_error is not None
    assert "UnknownTargetAPI" in result.api_error


async def test_local_system_propagates_tool_parameters():
    system = LocalMockSystem()
    result = await system.invoke("describe red", scenario="fetch_red")
    assert result.tool_parameters == {"name": "red"}