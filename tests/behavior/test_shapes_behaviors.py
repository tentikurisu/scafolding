"""Shape-API behavior matrix."""

from __future__ import annotations

import pytest

from repeatability_scaffold.behaviors.catalog import BEHAVIORS
from repeatability_scaffold.behaviors.expected_responses import matches_expected
from tests.conftest import run_n_times_async


@pytest.mark.parametrize("behavior", BEHAVIORS)
@pytest.mark.parametrize("scenario", ["describe_pentagon", "describe_unknown_shape"])
async def test_shapes_agent_message_for_behavior(
    scenario, behavior, execution_lambda, report_writer
):
    async def once():
        return await execution_lambda.handle(
            prompt="describe the shape",
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
        api="shapes",
        scenario=scenario,
        behavior=behavior,
        stage="agent_message_match",
        passes=pass_count,
        total=10,
        pass_rate=pass_count / 10,
    )

    assert pass_count == 10, (
        f"shapes/{scenario}/{behavior}: only {pass_count}/10 agent_messages "
        f"contained expected tokens\n"
        f"  sample failures: {failures[:3]}"
    )


@pytest.mark.parametrize("behavior", BEHAVIORS)
async def test_shapes_specific_behavior_contracts(behavior, execution_lambda):
    result = await execution_lambda.handle(
        prompt="describe the shape",
        scenario="describe_pentagon",
        behavior=behavior,
    )
    msg = result["agent_message"]

    if behavior == "successful":
        assert "pentagon" in msg.lower() or "five" in msg.lower() or "polygon" in msg.lower(), msg
    elif behavior == "empty":
        assert any(t in msg.lower() for t in ["unavailable", "missing", "not provided"]), msg
    elif behavior == "not_found":
        assert any(t in msg.lower() for t in ["not found", "couldn't find", "no record"]), msg
        # Must not invent a different shape name.
        for invented in ["pentagon", "hexagon", "triangle", "square", "circle"]:
            assert invented not in msg.lower().split(), (
                f"not_found shouldn't invent '{invented}': {msg!r}"
            )
    elif behavior == "missing_field":
        assert "pentagon" in msg.lower() or "partial" in msg.lower() or "missing" in msg.lower(), msg
    elif behavior == "malformed_payload":
        assert any(t in msg.lower() for t in ["unexpected", "malformed", "parsed"]), msg
    elif behavior == "api_400":
        assert any(t in msg.lower() for t in ["invalid", "bad request", "check"]), msg
    elif behavior == "api_401_403":
        assert any(t in msg.lower() for t in ["access", "permission", "authorized"]), msg
    elif behavior == "api_500":
        assert any(t in msg.lower() for t in ["service", "error", "try again"]), msg
    elif behavior == "timeout":
        assert any(t in msg.lower() for t in ["unavailable", "timed out", "try again"]), msg