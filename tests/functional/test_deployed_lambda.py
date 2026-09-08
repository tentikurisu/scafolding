"""Functional tests against the deployed Lambda. Opt-in only.

Required environment variables to enable:
    RUN_DEPLOYED_FUNCTIONAL_TESTS=true
    EXECUTION_LAMBDA_NAME=<your-lambda-name>
    AWS_REGION=<region>
    AWS credentials (any boto3-supported method)

Only runs scenarios with `run_against_deployed_lambda=True`. Never sends
mock behavior labels or internal scenario names. Raises immediately on
FunctionError. Supports direct Lambda and API Gateway response shapes.

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


def test_scenario_against_deployed_lambda(lambda_client):
    """Invoke the real Lambda for each opted-in scenario and assert semantic expectations.

    Not parametrized — avoids the empty-list-when-no-scenarios warning and
    gives a single skip with a clear reason.

    No mock behavior labels are sent. No internal scenario names leak
    into the Lambda event — we use build_lambda_event which only includes
    fields the real contract needs.
    """
    for scenario in _DEPLOYABLE:
        event = build_lambda_event(scenario)

        try:
            resp = lambda_client.invoke(
                FunctionName=os.environ["EXECUTION_LAMBDA_NAME"],
                InvocationType="RequestResponse",
                Payload=json.dumps(event).encode("utf-8"),
            )
        except Exception as exc:
            pytest.fail(f"{scenario.name}: Lambda invocation failed: {exc}")

        if resp.get("FunctionError"):
            body = resp.get("Payload")
            body_text = body.read().decode("utf-8") if body else ""
            pytest.fail(f"{scenario.name}: Lambda FunctionError: {body_text}")

        payload_bytes = resp.get("Payload")
        if payload_bytes is None:
            pytest.fail(f"{scenario.name}: Lambda returned empty Payload")

        raw = json.loads(payload_bytes.read().decode("utf-8"))

        # Handle API Gateway-style response: {statusCode, body}
        if isinstance(raw, dict) and "statusCode" in raw and "body" in raw:
            if raw["statusCode"] >= 400:
                pytest.fail(f"{scenario.name}: Lambda status {raw['statusCode']}: {raw.get('body')}")
            try:
                raw = json.loads(raw["body"])
            except json.JSONDecodeError:
                pytest.fail(f"{scenario.name}: Lambda body not valid JSON: {raw.get('body')}")

        result = normalize_response(raw)
        assert_scenario(result, scenario)