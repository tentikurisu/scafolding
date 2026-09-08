"""Central assertion function.

Every functional test calls `assert_scenario(result, scenario)`. The check
is permissive: assertions only fire when the result actually exposes the
data. If the production Lambda (deployed) doesn't return tool/API metadata,
those checks are skipped — we never invent data and never fail on missing
optional observability fields.

Real-LLM outputs are assessed semantically (required tokens appear,
forbidden tokens don't). We never require exact wording.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scenarios import Scenario
    from .project_adapter import ExecutionResult


def assert_scenario(result: "ExecutionResult", scenario: "Scenario") -> None:
    """Check observable fields of `result` against `scenario`.

    Skipped gracefully (not failed) when the result doesn't expose the
    field being checked.
    """

    # 1. Answer text is non-empty.
    assert result.answer_text, "Expected non-empty answer_text"

    # 2. Required tokens appear (case-insensitive).
    if scenario.expected_answer_tokens:
        text_lower = result.answer_text.lower()
        for token in scenario.expected_answer_tokens:
            assert token.lower() in text_lower, (
                f"Required token {token!r} not in answer_text: {result.answer_text!r}"
            )

    # 3. Forbidden tokens do NOT appear (hallucination guard).
    if scenario.forbidden_answer_tokens:
        text_lower = result.answer_text.lower()
        for token in scenario.forbidden_answer_tokens:
            assert token.lower() not in text_lower, (
                f"Forbidden token {token!r} found in answer_text: {result.answer_text!r}"
            )

    # 4. Expected API was selected (skip if result doesn't expose).
    if scenario.expected_api_name is not None and result.target_api is not None:
        assert result.target_api == scenario.expected_api_name, (
            f"Expected API {scenario.expected_api_name!r}, got {result.target_api!r}"
        )

    # 5. Expected parameters were supplied (skip if result doesn't expose).
    if scenario.expected_api_request is not None and result.tool_parameters is not None:
        assert result.tool_parameters == scenario.expected_api_request, (
            f"Expected parameters {scenario.expected_api_request!r}, "
            f"got {result.tool_parameters!r}"
        )

    # 6. Expected error category matches (skip if result doesn't expose).
    if scenario.expected_error_category is not None and result.api_error_category is not None:
        assert result.api_error_category == scenario.expected_error_category, (
            f"Expected error category {scenario.expected_error_category!r}, "
            f"got {result.api_error_category!r}"
        )