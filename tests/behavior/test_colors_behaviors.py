"""Color-API behavior matrix.

For each of the 9 placeholder behaviors, the lambda's agent_message must
match the expected keyword/regex set in `behaviors/expected_responses.py`.
"""

from __future__ import annotations

import pytest

from repeatability_scaffold.behaviors.catalog import BEHAVIORS
from repeatability_scaffold.behaviors.expected_responses import matches_expected
from tests.conftest import run_n_times_async


@pytest.mark.parametrize("behavior", BEHAVIORS)
@pytest.mark.parametrize("scenario", ["fetch_color_red", "fetch_color_xyz"])
async def test_colors_agent_message_for_behavior(
    scenario, behavior, execution_lambda, report_writer
):
    """Agent message for (colors scenario, behavior) must contain expected tokens."""
    async def once():
        return await execution_lambda.handle(
            prompt="describe the color",
            scenario=scenario,
            behavior=behavior,
        )

    results = await run_n_times_async(once, n=10)

    pass_count = 0
    failures: list[str] = []
    for r in results:
        ok, _reason = matches_expected(r["agent_message"], scenario, behavior)
        if ok:
            pass_count += 1
        else:
            failures.append(r["agent_message"])

    report_writer(
        api="colors",
        scenario=scenario,
        behavior=behavior,
        stage="agent_message_match",
        passes=pass_count,
        total=10,
        pass_rate=pass_count / 10,
    )

    assert pass_count == 10, (
        f"colors/{scenario}/{behavior}: only {pass_count}/10 agent_messages "
        f"contained expected tokens\n"
        f"  sample failures: {failures[:3]}"
    )


@pytest.mark.parametrize("behavior", BEHAVIORS)
async def test_colors_specific_behavior_contracts(behavior, execution_lambda):
    """Per-behavior semantic contracts (in addition to keyword match)."""
    result = await execution_lambda.handle(
        prompt="describe the color",
        scenario="fetch_color_red",
        behavior=behavior,
    )
    msg = result["agent_message"]

    if behavior == "successful":
        # Must reference actual color data, not generic filler.
        assert any(token in msg for token in ["red", "#FF0000", "complementary"]), (
            f"Successful color message didn't reference data: {msg!r}"
        )
    elif behavior == "empty":
        # Must NOT invent a specific hex code.
        assert "#FF0000" not in msg and "#" not in msg, (
            f"Empty message shouldn't contain hex codes: {msg!r}"
        )
    elif behavior == "not_found":
        # Must NOT invent a specific color name.
        for invented in ["red", "blue", "green"]:
            assert invented.lower() not in msg.lower().split(), (
                f"not_found message shouldn't invent '{invented}': {msg!r}"
            )
    elif behavior == "missing_field":
        # Must reference the available field (hex/name) but acknowledge missing data.
        assert any(t.lower() in msg.lower() for t in ["red", "#FF0000", "hex"]), msg
        assert any(t in msg.lower() for t in ["missing", "partial"]), msg
    elif behavior == "malformed_payload":
        # Must acknowledge unexpected data.
        assert any(t in msg.lower() for t in ["unexpected", "malformed", "parsed"]), msg
    elif behavior == "api_400":
        assert any(t in msg.lower() for t in ["invalid", "bad request", "check"]), msg
    elif behavior == "api_401_403":
        assert any(t in msg.lower() for t in ["access", "permission", "authorized"]), msg
    elif behavior == "api_500":
        assert any(t in msg.lower() for t in ["service", "error", "try again"]), msg
    elif behavior == "timeout":
        assert any(t in msg.lower() for t in ["unavailable", "timed out", "try again"]), msg