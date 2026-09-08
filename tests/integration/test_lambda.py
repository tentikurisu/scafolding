"""Integration tests against the real AWS Lambda. Skipped unless TEST_TARGET=lambda
AND EXECUTION_LAMBDA_NAME is set.

These verify the Lambda contract end-to-end:
  - Lambda can be invoked
  - Response shape matches ExecutionResult
  - Real scenarios produce the expected semantic tokens
"""
import os
import pytest
from scaffold.config import get_config
from scaffold.scenarios import scenarios_for_target
from scaffold.lambda_system import AwsLambdaSystem, LambdaInvocationError


pytestmark = pytest.mark.integration


def _has_lambda_config() -> bool:
    cfg = get_config()
    return cfg.test_target == "lambda" and bool(cfg.lambda_name)


@pytest.fixture(scope="module", autouse=True)
def _require_lambda():
    if not _has_lambda_config():
        pytest.skip(
            "Integration tests require TEST_TARGET=lambda AND EXECUTION_LAMBDA_NAME. "
            "Set them in env or .env to run."
        )


# === Lambda contract =======================================

def test_lambda_config_present():
    """Sanity: env vars set when TEST_TARGET=lambda."""
    cfg = get_config()
    assert cfg.lambda_name, "EXECUTION_LAMBDA_NAME must be set when TEST_TARGET=lambda"
    assert cfg.aws_region, "AWS_REGION must be set"


def test_lambda_system_constructs():
    """AwsLambdaSystem should construct without AWS calls (just config check)."""
    AwsLambdaSystem()  # raises if config invalid


@pytest.mark.real
async def test_lambda_invokes_safely():
    """Smoke test: invoke the Lambda with a simple prompt and get a result back."""
    system = AwsLambdaSystem()
    result = await system.invoke(
        prompt="hello",
        scenario="fetch_red",
    )
    # If we got here, the Lambda returned a parseable response.
    assert result.response_text is not None


# === Real-safe scenarios against the Lambda =================

@pytest.mark.real
@pytest.mark.parametrize(
    "scenario",
    [s for s in scenarios_for_target("lambda") if s.supports_real_target],
    ids=[f"{s.name}-{s.behavior}" for s in scenarios_for_target("lambda") if s.supports_real_target],
)
async def test_real_scenario_semantic_match(scenario):
    """Real-Lambda tests only assert semantic content; never exact strings."""
    from scaffold.validators import contains_all, contains_none

    system = AwsLambdaSystem()
    result = await system.invoke(scenario.prompt, scenario=scenario.name)
    assert result.response_text, "Lambda returned empty response"

    if scenario.expected_response_tokens:
        assert contains_all(result.response_text, scenario.expected_response_tokens), (
            f"Missing required tokens in real response: {result.response_text!r}"
        )
    if scenario.forbidden_response_tokens:
        assert contains_none(result.response_text, scenario.forbidden_response_tokens), (
            f"Forbidden tokens found in real response: {result.response_text!r}"
        )


# === Failure mode =========================================

@pytest.mark.real
async def test_lambda_invocation_error_handled():
    """Bad input produces a clear error, not a silent failure."""
    system = AwsLambdaSystem()
    with pytest.raises(LambdaInvocationError):
        # Force failure with a clearly bad payload
        await system.invoke(prompt="", scenario="__definitely_does_not_exist__")