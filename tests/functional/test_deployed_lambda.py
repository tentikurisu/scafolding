"""Functional tests against the deployed Lambda. Opt-in only.

Required environment variables to enable:
    RUN_DEPLOYED_FUNCTIONAL_TESTS=true
    EXECUTION_LAMBDA_NAME=<your-lambda-name>
    AWS_REGION=<region>
    AWS credentials (any boto3-supported method)

Only runs scenarios with `run_against_deployed_lambda=True`. Each scenario
runs `scenario.run_count` times; the test requires pass rate >=
`scenario.minimum_pass_rate`. Never sends mock behavior labels or internal
scenario names. Raises immediately on FunctionError. Supports direct
Lambda and API Gateway response shapes.

Single compact flow so the Lambda is not invoked repeatedly across
overlapping test functions.

The entire module is skipped when:
  - No scenarios have run_against_deployed_lambda=True, OR
  - RUN_DEPLOYED_FUNCTIONAL_TESTS is not "true", OR
  - Required env vars are missing.

This means an ordinary pytest run never contacts AWS.
"""

from __future__ import annotations

import json
import os

import pytest

from .assertions import assert_scenario
from .project_adapter import build_lambda_event, normalize_response
from .scenarios import deployed_scenarios


pytestmark = pytest.mark.deployed


_DEPLOYABLE = deployed_scenarios()


def _deployed_prerequisites_met() -> bool:
    return (
        bool(_DEPLOYABLE)
        and os.environ.get("RUN_DEPLOYED_FUNCTIONAL_TESTS", "").lower() == "true"
        and bool(os.environ.get("EXECUTION_LAMBDA_NAME"))
        and bool(os.environ.get("AWS_REGION"))
    )


@pytest.fixture
def lambda_client():
    """A boto3 Lambda client. Skip cleanly if prerequisites missing."""
    if not _deployed_prerequisites_met():
        pytest.skip(
            "Deployed Lambda tests require RUN_DEPLOYED_FUNCTIONAL_TESTS=true, "
            "EXECUTION_LAMBDA_NAME, AWS_REGION, and at least one scenario with "
            "run_against_deployed_lambda=True."
        )
    try:
        import boto3
    except ImportError as exc:
        pytest.skip(f"boto3 not installed: {exc}")
    return boto3.client("lambda", region_name=os.environ["AWS_REGION"])


def _invoke_once(lambda_client, scenario) -> tuple[bool, str]:
    """Invoke the Lambda once for this scenario. Returns (ok, failure_reason)."""
    event = build_lambda_event(scenario)

    try:
        resp = lambda_client.invoke(
            FunctionName=os.environ["EXECUTION_LAMBDA_NAME"],
            InvocationType="RequestResponse",
            Payload=json.dumps(event).encode("utf-8"),
        )
    except Exception as exc:
        return False, f"Lambda invocation failed: {exc}"

    if resp.get("FunctionError"):
        body = resp.get("Payload")
        body_text = body.read().decode("utf-8") if body else ""
        return False, f"Lambda FunctionError: {body_text}"

    payload_bytes = resp.get("Payload")
    if payload_bytes is None:
        return False, "Lambda returned empty Payload"

    try:
        raw = json.loads(payload_bytes.read().decode("utf-8"))
    except json.JSONDecodeError:
        return False, "Lambda payload not valid JSON"

    # Handle API Gateway-style response: {statusCode, body}
    if isinstance(raw, dict) and "statusCode" in raw and "body" in raw:
        if raw["statusCode"] >= 400:
            return False, f"Lambda status {raw['statusCode']}: {raw.get('body')}"
        try:
            raw = json.loads(raw["body"])
        except json.JSONDecodeError:
            return False, "Lambda body not valid JSON"

    result = normalize_response(raw)
    try:
        assert_scenario(result, scenario)
        return True, ""
    except AssertionError as e:
        return False, str(e)


def test_deployed_scenarios(lambda_client):
    """For each opted-in scenario, run it `run_count` times and require
    `minimum_pass_rate`.

    Single test function so the Lambda isn't invoked by separate tests
    for the same scenario. No mock behavior labels are sent. No internal
    scenario names leak into the Lambda event.
    """
    for scenario in _DEPLOYABLE:
        n = max(1, scenario.run_count)
        passes = 0
        failures: list = []
        for _ in range(n):
            ok, reason = _invoke_once(lambda_client, scenario)
            if ok:
                passes += 1
            elif len(failures) < 3:
                failures.append(reason)

        rate = passes / n
        assert rate >= scenario.minimum_pass_rate, (
            f"{scenario.name}: pass rate {rate:.2f} < required "
            f"{scenario.minimum_pass_rate:.2f}. Sample failures: {failures}"
        )