"""Functional tests: invoke the actual production handler with mocked deps.

These tests do NOT recreate orchestration logic. They call the real
handler loaded from `project_adapter.load_production_handler()` with
mocked LLM/API dependencies installed via
`project_adapter.install_test_dependencies()`.

The only thing the test does:
    1. Build mocks from the scenario.
    2. Patch production dependencies.
    3. Call production_handler(event, ctx).
    4. Normalize the response.
    5. Assert against the scenario.

Production handlers in the destination repo are expected to have the
shape:

    def lambda_handler(event, context):
        return execute(
            event,
            llm=create_llm(),
            api_registry=create_api_registry(),
        )

    def execute(event, llm, api_registry):
        ...

If your handler does not expose dependency injection this cleanly, use
monkeypatch in `install_test_dependencies()` to swap the underlying
client factories.
"""

from __future__ import annotations

import asyncio

import pytest

from .assertions import assert_scenario
from .mocks import ConfigurableMockAPI
from .project_adapter import (
    ExecutionResult,
    build_lambda_event,
    install_test_dependencies,
    load_production_handler,
    normalize_response,
)
from .scenarios import local_scenarios


pytestmark = pytest.mark.functional


# === Stub LLM (deterministic, scenario-aware) =========================

class _StubLLM:
    """A stub LLM that mirrors what the scenario expects.

    Tests pass this in via `install_test_dependencies`. Real production
    LLMs would call AWS Bedrock / OpenAI / etc.
    """

    def __init__(self, scenario) -> None:
        self.scenario = scenario

    async def first_call(self, prompt: str, scenario_name: str) -> dict:
        """Pick the expected API and use the expected parameters."""
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
        """Build an answer that satisfies the scenario's token expectations."""
        if api_error is not None:
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
        if api_response is None:
            return "Record not found."
        tokens = self.scenario.expected_answer_tokens
        return " ".join(tokens) if tokens else "Done."


# === Per-scenario mocks ============================================

def _make_mocks(scenario) -> dict:
    """Build the LLM stub + API registry for one scenario."""
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
    raw = await handler(event, fake_context)
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


@pytest.mark.parametrize("scenario", _LOCAL, ids=[s.name for s in _LOCAL])
async def test_scenario_repeatability(scenario, handler, fake_context, monkeypatch):
    """Run the scenario N times; require minimum_pass_rate.

    Note: this test does NOT also assert per-run semantic correctness
    via assert_scenario (that would contradict minimum_pass_rate).
    """
    mocks = _make_mocks(scenario)
    install_test_dependencies(monkeypatch, mocks)

    event = build_lambda_event(scenario)
    n = max(1, scenario.run_count)
    passes = 0
    last_failure: str = ""
    for _ in range(n):
        raw = await handler(event, fake_context)
        result = normalize_response(raw)
        try:
            assert_scenario(result, scenario)
            passes += 1
        except AssertionError as e:
            last_failure = str(e)

    rate = passes / n
    assert rate >= scenario.minimum_pass_rate, (
        f"{scenario.name}: pass rate {rate:.2f} < required {scenario.minimum_pass_rate:.2f}. "
        f"Last failure: {last_failure}"
    )