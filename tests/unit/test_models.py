"""Unit tests for Pydantic models."""
import pytest
from pydantic import ValidationError
from scaffold.models import ExecutionResult, Scenario


def test_execution_result_minimal():
    r = ExecutionResult(response_text="hello")
    assert r.response_text == "hello"
    assert r.target_api is None
    assert r.tool_parameters == {}
    assert r.api_response is None
    assert r.api_error is None


def test_execution_result_full():
    r = ExecutionResult(
        response_text="hello",
        target_api="colors",
        tool_parameters={"name": "red"},
        api_response={"name": "red", "hex": "#FF0000"},
        api_error=None,
    )
    assert r.target_api == "colors"
    assert r.tool_parameters == {"name": "red"}


def test_execution_result_no_mutable_defaults_shared():
    """Each instance must get its own dict (not share the default)."""
    r1 = ExecutionResult(response_text="x")
    r2 = ExecutionResult(response_text="y")
    r1.tool_parameters["k"] = "v"
    assert "k" not in r2.tool_parameters


def test_execution_result_extra_fields_ignored():
    r = ExecutionResult(response_text="x", unknown_field="ignored")
    assert not hasattr(r, "unknown_field")


def test_scenario_minimal():
    s = Scenario(name="foo", prompt="bar")
    assert s.name == "foo"
    assert s.behavior == "successful"
    assert s.minimum_pass_rate == 1.0
    assert s.run_count == 10
    assert s.supports_real_target is True


def test_scenario_no_mutable_defaults_shared():
    s1 = Scenario(name="a", prompt="b")
    s2 = Scenario(name="c", prompt="d")
    s1.expected_response_tokens.append("x")
    assert "x" not in s2.expected_response_tokens


def test_scenario_with_all_fields():
    s = Scenario(
        name="fetch_red",
        prompt="describe red",
        behavior="successful",
        expected_target_api="colors",
        expected_tool_parameters={"name": "red"},
        expected_response_tokens=["red", "#FF0000"],
        forbidden_response_tokens=["blue"],
        expected_api_fields={"hex": "#FF0000"},
        expected_error_category="success",
        minimum_pass_rate=0.9,
        run_count=5,
        supports_real_target=False,
        notes="demo",
    )
    assert s.expected_target_api == "colors"
    assert s.minimum_pass_rate == 0.9
    assert s.supports_real_target is False