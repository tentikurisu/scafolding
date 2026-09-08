"""Unit tests for the central assert_scenario function."""

import pytest

from tests.functional.assertions import assert_scenario
from tests.functional.project_adapter import ExecutionResult
from tests.functional.scenarios import Scenario


pytestmark = pytest.mark.unit


def _scenario(**overrides) -> Scenario:
    base = dict(
        name="t",
        question="q",
    )
    base.update(overrides)
    return Scenario(**base)


def test_empty_answer_fails():
    s = _scenario()
    r = ExecutionResult(answer_text="")
    with pytest.raises(AssertionError, match="non-empty"):
        assert_scenario(r, s)


def test_required_token_present():
    s = _scenario(expected_answer_tokens=("hello",))
    r = ExecutionResult(answer_text="hello world")
    assert_scenario(r, s)


def test_required_token_missing_fails():
    s = _scenario(expected_answer_tokens=("hello",))
    r = ExecutionResult(answer_text="goodbye world")
    with pytest.raises(AssertionError, match="hello"):
        assert_scenario(r, s)


def test_required_token_case_insensitive():
    s = _scenario(expected_answer_tokens=("HELLO",))
    r = ExecutionResult(answer_text="hello world")
    assert_scenario(r, s)


def test_forbidden_token_present_fails():
    s = _scenario(forbidden_answer_tokens=("password",))
    r = ExecutionResult(answer_text="leaked password here")
    with pytest.raises(AssertionError, match="password"):
        assert_scenario(r, s)


def test_forbidden_token_absent_passes():
    s = _scenario(forbidden_answer_tokens=("password",))
    r = ExecutionResult(answer_text="all good")
    assert_scenario(r, s)


def test_target_api_match_passes():
    s = _scenario(expected_api_name="records")
    r = ExecutionResult(answer_text="ok", target_api="records")
    assert_scenario(r, s)


def test_target_api_mismatch_fails():
    s = _scenario(expected_api_name="records")
    r = ExecutionResult(answer_text="ok", target_api="users")
    with pytest.raises(AssertionError, match="records"):
        assert_scenario(r, s)


def test_target_api_check_skipped_when_result_lacks_field():
    s = _scenario(expected_api_name="records")
    r = ExecutionResult(answer_text="ok", target_api=None)  # not exposed
    assert_scenario(r, s)  # graceful skip


def test_parameters_match_passes():
    s = _scenario(expected_api_request={"asset_id": "X"})
    r = ExecutionResult(answer_text="ok", tool_parameters={"asset_id": "X"})
    assert_scenario(r, s)


def test_parameters_mismatch_fails():
    s = _scenario(expected_api_request={"asset_id": "X"})
    r = ExecutionResult(answer_text="ok", tool_parameters={"asset_id": "Y"})
    with pytest.raises(AssertionError):
        assert_scenario(r, s)


def test_parameters_check_skipped_when_result_lacks_field():
    s = _scenario(expected_api_request={"asset_id": "X"})
    r = ExecutionResult(answer_text="ok", tool_parameters=None)
    assert_scenario(r, s)


def test_error_category_match_passes():
    s = _scenario(expected_error_category="timeout")
    r = ExecutionResult(answer_text="timeout", api_error_category="timeout")
    assert_scenario(r, s)


def test_error_category_mismatch_fails():
    s = _scenario(expected_error_category="timeout")
    r = ExecutionResult(answer_text="timeout", api_error_category="server_error")
    with pytest.raises(AssertionError):
        assert_scenario(r, s)


def test_error_category_check_skipped_when_result_lacks_field():
    s = _scenario(expected_error_category="timeout")
    r = ExecutionResult(answer_text="timeout", api_error_category=None)
    assert_scenario(r, s)


def test_full_happy_path_passes():
    s = _scenario(
        expected_api_name="records",
        expected_api_request={"asset_id": "TEST-001"},
        expected_answer_tokens=("active",),
        forbidden_answer_tokens=("password",),
    )
    r = ExecutionResult(
        answer_text="Record TEST-001 is active.",
        target_api="records",
        tool_parameters={"asset_id": "TEST-001"},
    )
    assert_scenario(r, s)


def test_full_error_path_passes():
    s = _scenario(
        expected_api_name="records",
        expected_api_request={"asset_id": "TEST-002"},
        mock_api_exception=TimeoutError("simulated"),
        expected_answer_tokens=("unavailable", "timed out"),
        expected_error_category="timeout",
    )
    r = ExecutionResult(
        answer_text="The service is unavailable; the request timed out.",
        target_api=None,
        api_error="TimeoutError",
        api_error_category="timeout",
    )
    assert_scenario(r, s)


import pytest  # at the end so other functions don't see it before assertions defined