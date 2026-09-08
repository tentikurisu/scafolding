"""Functional tests: scenarios run against the SystemUnderTest.

Tests are parametrized over the central SCENARIOS collection. Adding a new
scenario = adding one object in scaffold/scenarios.py.

The `system_under_test` and `config` fixtures come from conftest.py.
"""
import pytest
from scaffold.config import get_config
from scaffold.scenarios import scenarios_for_target
from scaffold.lambda_system import LambdaInvocationError
from scaffold.validators import (
    category_for_error,
    contains_all,
    contains_none,
    fields_match,
    fields_match_report,
    jaccard,
)


pytestmark = pytest.mark.functional


def _parametrize_scenarios():
    cfg = get_config()
    scenarios = scenarios_for_target(cfg.test_target)
    ids = [f"{s.name}-{s.behavior}" for s in scenarios]
    return pytest.mark.parametrize(
        "scenario",
        scenarios,
        ids=ids,
    )


# === Scenario execution =============================================

@_parametrize_scenarios()
async def test_scenario_invocation_succeeds(scenario, system_under_test):
    """The system-under-test successfully invokes the agent for this scenario."""
    result = await system_under_test.invoke(
        scenario.prompt, scenario=scenario.name, behavior=scenario.behavior,
    )
    assert result is not None
    assert result.response_text is not None


@_parametrize_scenarios()
async def test_scenario_response_contains_required_tokens(scenario, system_under_test):
    """agent_message must contain all expected_response_tokens (semantic check)."""
    if not scenario.expected_response_tokens:
        pytest.skip("No required tokens configured for this scenario")
    result = await system_under_test.invoke(
        scenario.prompt, scenario=scenario.name, behavior=scenario.behavior,
    )
    assert contains_all(result.response_text, scenario.expected_response_tokens), (
        f"Missing tokens {scenario.expected_response_tokens} in response: {result.response_text!r}"
    )


@_parametrize_scenarios()
async def test_scenario_avoids_forbidden_tokens(scenario, system_under_test):
    """agent_message must NOT contain forbidden_response_tokens (hallucination check)."""
    if not scenario.forbidden_response_tokens:
        pytest.skip("No forbidden tokens configured for this scenario")
    result = await system_under_test.invoke(
        scenario.prompt, scenario=scenario.name, behavior=scenario.behavior,
    )
    assert contains_none(result.response_text, scenario.forbidden_response_tokens), (
        f"Forbidden tokens found in response: {result.response_text!r}"
    )


# === Repeatability =======================================

@_parametrize_scenarios()
async def test_scenario_repeatability(scenario, system_under_test, config):
    """Repeated runs achieve at least minimum_pass_rate."""
    n = scenario.run_count
    results = []
    for _ in range(n):
        results.append(await system_under_test.invoke(
            scenario.prompt, scenario=scenario.name, behavior=scenario.behavior,
        ))
    passes = sum(
        1 for r in results
        if contains_all(r.response_text, scenario.expected_response_tokens)
    )
    rate = passes / n
    assert rate >= scenario.minimum_pass_rate, (
        f"{scenario.name}: pass rate {rate:.2f} < required {scenario.minimum_pass_rate:.2f}"
    )


# === Mock-only fault injection =======================================

@_parametrize_scenarios()
@pytest.mark.mock_only
async def test_scenario_simulated_errors(scenario, system_under_test):
    """Mock-only: with fault injection, error behaviors raise or produce errors.

    Skipped automatically on the Lambda target via mock_only marker.
    """
    cfg = get_config()
    if cfg.test_target != "mock":
        pytest.skip("Mock-only fault injection; skipped on Lambda target")
    if not scenario.behavior.startswith("api_") and scenario.behavior not in (
        "timeout", "malformed_payload", "missing_field", "not_found", "empty",
    ):
        pytest.skip(f"Behavior {scenario.behavior} not a fault behavior")

    from scaffold.mock_system import LocalMockSystem
    if not isinstance(system_under_test, LocalMockSystem):
        pytest.skip("Not a LocalMockSystem")

    result = await system_under_test.invoke(
        scenario.prompt, scenario=scenario.name, behavior=scenario.behavior,
    )
    if scenario.behavior == "not_found":
        assert result.api_response is None
    elif scenario.behavior == "empty":
        assert result.api_response == {}
    elif scenario.behavior in ("api_400", "api_500", "timeout", "api_401_403"):
        assert result.api_error is not None
        assert result.api_error_category in (
            "client_error", "server_error", "timeout", "auth_error",
        )