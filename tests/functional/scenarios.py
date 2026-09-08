"""Central scenario definitions.

Each Scenario owns its mock API request/response shape so adding a real
business API only changes this file (and the project_adapter). Fictional
scenarios default to `run_against_deployed_lambda=False` and must NEVER be
flipped to True — they describe made-up examples, not real contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Scenario:
    """A single test scenario.

    The harness never invents metadata; every assertion either finds what
    it needs in the ExecutionResult or is skipped. Required tokens express
    requirements, not observed output — do not codify current model
    behaviour into the tokens.
    """

    name: str
    question: str

    # Routing expectations — only asserted when the result actually exposes them.
    expected_api_name: Optional[str] = None
    expected_api_request: Optional[dict] = None

    # Mock configuration for local tests.
    mock_api_response: Optional[dict | list] = None
    mock_api_exception: Optional[BaseException] = None

    # Semantic expectations on the final answer.
    expected_answer_tokens: tuple[str, ...] = ()
    forbidden_answer_tokens: tuple[str, ...] = ()

    # Expected coarse error category (timeout / server_error / client_error /
    # auth_error / not_found). Only asserted if the production result exposes one.
    expected_error_category: Optional[str] = None

    # Repeatability: how many runs, what fraction must pass.
    run_count: int = 1
    minimum_pass_rate: float = 1.0

    # Deployed Lambda opt-in. Fictional scenarios MUST stay False.
    run_against_deployed_lambda: bool = False


# === Fictional examples ============================================
# These demonstrate the harness. Replace with real business scenarios
# derived from requirements and API contracts (not from observed output).

SCENARIOS: list[Scenario] = [
    Scenario(
        name="fetch_record_success",
        question="look up record TEST-001",
        expected_api_name="records",
        expected_api_request={"asset_id": "TEST-001"},
        mock_api_response={
            "result": {"id": "TEST-001", "currentStatus": "active"},
        },
        expected_answer_tokens=("TEST-001", "active"),
        run_count=1,
    ),
    Scenario(
        name="fetch_record_not_found",
        question="look up record DOES-NOT-EXIST",
        expected_api_name="records",
        expected_api_request={"asset_id": "DOES-NOT-EXIST"},
        mock_api_response=None,
        expected_answer_tokens=("not found",),
        forbidden_answer_tokens=("active", "TEST-001"),
        expected_error_category="not_found",
        run_count=1,
    ),
    Scenario(
        name="fetch_record_timeout",
        question="look up record TEST-002",
        expected_api_name="records",
        expected_api_request={"asset_id": "TEST-002"},
        mock_api_exception=TimeoutError("simulated timeout"),
        expected_answer_tokens=("unavailable", "timed out"),
        expected_error_category="timeout",
        run_count=1,
    ),
    Scenario(
        name="fetch_record_server_error",
        question="look up record TEST-003",
        expected_api_name="records",
        expected_api_request={"asset_id": "TEST-003"},
        mock_api_exception=RuntimeError("internal server error"),
        expected_answer_tokens=("error", "service"),
        expected_error_category="server_error",
        run_count=1,
    ),
    Scenario(
        name="fetch_record_auth_failure",
        question="look up record TEST-004",
        expected_api_name="records",
        expected_api_request={"asset_id": "TEST-004"},
        mock_api_exception=PermissionError("not authorized"),
        expected_answer_tokens=("access",),
        expected_error_category="auth_error",
        run_count=1,
    ),
    Scenario(
        name="fetch_record_bad_request",
        question="look up record with empty id",
        expected_api_name="records",
        expected_api_request={"asset_id": ""},
        mock_api_exception=ValueError("invalid asset_id"),
        expected_answer_tokens=("invalid",),
        expected_error_category="client_error",
        run_count=1,
    ),
]


def local_scenarios() -> list[Scenario]:
    """Scenarios that can be run locally with mocks (never deployed)."""
    return [s for s in SCENARIOS if not s.run_against_deployed_lambda]


def deployed_scenarios() -> list[Scenario]:
    """Scenarios explicitly opted in to deployed Lambda execution."""
    return [s for s in SCENARIOS if s.run_against_deployed_lambda]