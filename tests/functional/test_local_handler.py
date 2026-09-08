"""Functional tests: invoke the actual production handler with mocked deps.

These tests do NOT recreate orchestration logic. They call the real
handler loaded from `project_adapter.load_production_handler()` with
mocked LLM/API dependencies installed via
`project_adapter.install_test_dependencies()`.

The test:
  1. Builds mocks from the scenario.
  2. Patches production dependencies.
  3. Calls the production handler (sync or async).
  4. Normalizes the response.
  5. Asserts against the scenario.
  6. Verifies the request actually reached the API.
  7. Verifies the production handler passed the API response to the LLM.
"""

from __future__ import annotations

import pytest

from .assertions import assert_scenario
from .mocks import ConfigurableMockAPI
from .project_adapter import (
    ExecutionResult,
    build_lambda_event,
    install_test_dependencies,
    invoke_handler,
    load_production_handler,
    normalize_response,
)
from .scenarios import Scenario, local_scenarios


pytestmark = pytest.mark.functional


# === Stub LLM: derives answer from api_response, records inputs =========

class _StubLLM:
    """A stub LLM whose answer is built from the api_response it receives.

    This proves the production handler correctly threaded the api_response
    through to the second LLM call. The tests assert that
    `second_call_inputs[-1]["api_response"] == scenario.mock_api_response`.
    """

    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.first_call_inputs: list = []
        self.second_call_inputs: list = []

    async def first_call(self, prompt: str, scenario_name: str) -> dict:
        self.first_call_inputs.append({"prompt": prompt, "scenario_name": scenario_name})
        return {
            "action": "fetch",
            "target_api": self.scenario.expected_api_name or "",
            "parameters": self.scenario.expected_api_request or {},
            "reasoning": "stub LLM",
        }

    async def second_call(
        self,
        scenario_name: str,
        behavior: str,
        api_response,
        api_error,
    ) -> str:
        # Record the full input so tests can verify what the production
        # handler actually passed to the LLM.
        self.second_call_inputs.append({
            "behavior": behavior,
            "api_response": api_response,
            "api_error": api_error,
        })
        if api_error is not None:
            return self._format_error(api_error)
        return self._format_response(api_response)

    def _format_error(self, api_error) -> str:
        err_name = (
            api_error if isinstance(api_error, str)
            else type(api_error).__name__
        ).lower()
        if "timeout" in err_name:
            return "The service is unavailable; the request timed out."
        if "permission" in err_name or "auth" in err_name:
            return "I do not have access to the records service."
        if "value" in err_name:
            return "The request was invalid; please check the input."
        return "There was a service error."

    def _format_response(self, api_response) -> str:
        """Build an answer from the api_response content.

        The answer derives from the response, not from a hard-coded token
        list. This is what makes the test prove the handler uses the
        real API response.
        """
        if api_response is None:
            return "Record not found."

        if isinstance(api_response, list):
            if not api_response:
                return "No records found."
            parts = []
            for r in api_response[:5]:
                if isinstance(r, dict):
                    rid = r.get("id", "?")
                    status = r.get("currentStatus") or r.get("status")
                    if status:
                        parts.append(f"{rid} status {status}")
                    else:
                        parts.append(str(rid))
            joined = ", ".join(parts) if parts else "(no ids)"
            return f"Found {len(api_response)} record(s): {joined}."

        if isinstance(api_response, dict):
            if not api_response:
                return "The response was empty."
            result = api_response.get("result", api_response)
            if not isinstance(result, dict):
                return "The data was unexpected."
            if not result:
                return "The response was empty."
            rid = _find_id(result)
            status = _find_status(result)
            parts = []
            parts.append(f"Record {rid}" if rid else "Record")
            if status:
                parts.append(f"status is {status}")
            else:
                parts.append("status unavailable")
            return " ".join(parts) + "."

        # Malformed (string, number, etc.)
        return "The data was unexpected."


def _find_id(d: dict) -> Optional[str]:
    if not isinstance(d, dict):
        return None
    return d.get("id") or d.get("record_id") or d.get("asset_id")


def _find_status(d: dict) -> Optional[str]:
    if not isinstance(d, dict):
        return None
    for key in ("currentStatus", "status", "state"):
        if key in d:
            return d[key]
    metadata = d.get("metadata", {})
    if isinstance(metadata, dict):
        for key in ("currentStatus", "status", "state"):
            if key in metadata:
                return metadata[key]
    return None


# === Per-scenario mocks ============================================

def _make_mocks(scenario: Scenario) -> dict:
    llm = _StubLLM(scenario)
    api = ConfigurableMockAPI(
        response=scenario.mock_api_response,
        expected_request=scenario.expected_api_request,
        exception=scenario.mock_api_exception,
    )
    registry: dict = {}
    if scenario.expected_api_name:
        registry[scenario.expected_api_name] = api
    return {"llm": llm, "registry": registry, "api": api}


# === Fixtures ======================================================

@pytest.fixture
def handler():
    """The actual production handler (or placeholder until adapted)."""
    return load_production_handler()


_LOCAL = local_scenarios()


# === Tests =========================================================

@pytest.mark.parametrize("scenario", _LOCAL, ids=[s.name for s in _LOCAL])
async def test_scenario_against_actual_handler(scenario, handler, fake_context, monkeypatch):
    """Invoke the real handler with mocks; assert against the scenario."""
    mocks = _make_mocks(scenario)
    install_test_dependencies(monkeypatch, mocks)

    event = build_lambda_event(scenario)
    raw = await invoke_handler(handler, event, fake_context)
    result = normalize_response(raw)

    assert_scenario(result, scenario)

    # Verify the request actually reached the API (not just what LLM said).
    if scenario.expected_api_name and scenario.expected_api_request is not None:
        assert mocks["api"].calls, "Mock API was never called"
        assert mocks["api"].calls[-1] == scenario.expected_api_request, (
            f"Mock API received unexpected request.\n"
            f"  expected: {scenario.expected_api_request!r}\n"
            f"  received: {mocks['api'].calls[-1]!r}"
        )

    # Verify the production handler passed the api_response to the LLM
    # in its second call. This proves the handler actually USED the API
    # response (rather than the LLM answer coming from somewhere else).
    if scenario.expected_api_name and mocks["llm"].second_call_inputs:
        last = mocks["llm"].second_call_inputs[-1]
        if scenario.mock_api_exception is None:
            assert last["api_response"] == scenario.mock_api_response, (
                f"Handler did not pass api_response to second LLM call.\n"
                f"  expected: {scenario.mock_api_response!r}\n"
                f"  got: {last['api_response']!r}"
            )
        else:
            # Error path: verify the error name reached the LLM.
            assert last["api_error"] is not None, (
                "Handler did not pass api_error to second LLM call."
            )


@pytest.mark.parametrize("scenario", _LOCAL, ids=[s.name for s in _LOCAL])
async def test_scenario_repeatability(scenario, handler, fake_context, monkeypatch):
    """Run the scenario N times; require minimum_pass_rate.

    For scenarios with minimum_pass_rate < 1.0 (real LLM scenarios),
    the test passes if enough runs satisfy assert_scenario.
    """
    mocks = _make_mocks(scenario)
    install_test_dependencies(monkeypatch, mocks)

    event = build_lambda_event(scenario)
    n = max(1, scenario.run_count)
    passes = 0
    failures: list = []
    for _ in range(n):
        raw = await invoke_handler(handler, event, fake_context)
        result = normalize_response(raw)
        try:
            assert_scenario(result, scenario)
            passes += 1
        except AssertionError as e:
            if len(failures) < 3:
                failures.append(str(e))

    rate = passes / n
    assert rate >= scenario.minimum_pass_rate, (
        f"{scenario.name}: pass rate {rate:.2f} < required {scenario.minimum_pass_rate:.2f}. "
        f"Sample failures: {failures}"
    )