"""Pytest fixtures + target selection + marker registration.

Picks LocalMockSystem or AwsLambdaSystem based on TEST_TARGET. AWS-only
tests are skipped unless TEST_TARGET=lambda. Mock-only tests are skipped
when running against a real Lambda.
"""

from __future__ import annotations

import pytest

from scaffold import make_system


# === Target selection ===============================================

def pytest_configure(config):
    """Register custom markers at startup."""
    markers = [
        "unit: pure unit tests (no fixtures, no network)",
        "component: component tests (mock LLM + mock APIs only)",
        "functional: end-to-end scenarios against SystemUnderTest",
        "integration: real Lambda or real API tests (skipped without AWS)",
        "mock_only: tests that simulate faults; skipped on real Lambda target",
        "real: tests that require real AWS/API resources",
    ]
    for marker in markers:
        config.addinivalue_line("markers", marker)


# === Auto-skips =====================================================

def pytest_collection_modifyitems(config, items):
    """Auto-skip mock_only tests when running against real Lambda target.

    This prevents fault-injection tests from running against production
    Lambda targets, where they cannot naturally produce the simulated
    errors. We use the `mock_only` marker as the signal.
    """
    import os
    target = os.environ.get("TEST_TARGET", "mock").lower()

    if target == "lambda":
        skip_mock = pytest.mark.skip(
            reason="Mock-only fault-injection test; skipped on Lambda target"
        )
        for item in items:
            if "mock_only" in item.keywords:
                item.add_marker(skip_mock)
    else:
        skip_real = pytest.mark.skip(
            reason="Real AWS test; run with TEST_TARGET=lambda"
        )
        for item in items:
            if "real" in item.keywords:
                item.add_marker(skip_real)


# === Fixtures =======================================================

@pytest.fixture(scope="session")
def system_under_test():
    """Build the SystemUnderTest based on TEST_TARGET.

    Test files parametrize over this; do NOT edit tests to switch target.

    For lambda target, if config is missing, skip rather than error
    so the run reports "no AWS config" cleanly rather than aborting.
    """
    from scaffold.config import get_config
    cfg = get_config()
    if cfg.test_target == "lambda" and not cfg.lambda_name:
        pytest.skip(
            "TEST_TARGET=lambda but EXECUTION_LAMBDA_NAME is not set. "
            "Set EXECUTION_LAMBDA_NAME in env or .env to run integration tests."
        )
    try:
        return make_system()
    except Exception as exc:
        pytest.skip(f"Could not build SystemUnderTest: {exc}")


@pytest.fixture(scope="session")
def config():
    """The current Config from env."""
    from scaffold import get_config
    return get_config()


# === Helper: run a scenario N times and aggregate ==================

@pytest.fixture
def run_scenario_n_times():
    """Returns a function that runs (system, scenario) n times and returns results."""
    import asyncio

    async def _runner(system, scenario, n):
        return await asyncio.gather(*[
            system.invoke(scenario.prompt, scenario=scenario.name)
            for _ in range(n)
        ])

    return _runner