"""Number-API behavior matrix."""

from __future__ import annotations

import pytest

from repeatability_scaffold.behaviors.catalog import BEHAVIORS
from repeatability_scaffold.behaviors.expected_responses import matches_expected
from tests.conftest import run_n_times_async


@pytest.mark.parametrize("behavior", BEHAVIORS)
@pytest.mark.parametrize("scenario", ["check_prime_17", "check_negative_number"])
async def test_numbers_agent_message_for_behavior(
    scenario, behavior, execution_lambda, report_writer
):
    async def once():
        return await execution_lambda.handle(
            prompt="check the number",
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
        api="numbers",
        scenario=scenario,
        behavior=behavior,
        stage="agent_message_match",
        passes=pass_count,
        total=10,
        pass_rate=pass_count / 10,
    )

    assert pass_count == 10, (
        f"numbers/{scenario}/{behavior}: only {pass_count}/10 agent_messages "
        f"contained expected tokens\n"
        f"  sample failures: {failures[:3]}"
    )


@pytest.mark.parametrize("behavior", BEHAVIORS)
async def test_numbers_specific_behavior_contracts(behavior, execution_lambda):
    result = await execution_lambda.handle(
        prompt="check the number",
        scenario="check_prime_17",
        behavior=behavior,
    )
    msg = result["agent_message"]

    if behavior == "successful":
        assert any(t in msg.lower() for t in ["prime", "17", "yes", "odd"]), msg
        assert "false" not in msg.lower() or "is not" in msg.lower()  # not flat "false"
    elif behavior == "empty":
        assert any(t in msg.lower() for t in ["unavailable", "missing", "not provided"]), msg
    elif behavior == "not_found":
        assert any(t in msg.lower() for t in ["not found", "couldn't find", "no record"]), msg
    elif behavior == "missing_field":
        assert "17" in msg or "-7" in msg or "partial" in msg.lower(), msg
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


async def test_numbers_negative_number_does_not_say_prime(execution_lambda):
    """Edge case: negative numbers are not prime. Agent must not say 'prime' for -7."""
    result = await execution_lambda.handle(
        prompt="check -7",
        scenario="check_negative_number",
        behavior="successful",
    )
    msg = result["agent_message"].lower()
    assert "not" in msg or "isn't" in msg or "is not" in msg, (
        f"Expected 'not prime' framing for -7: {result['agent_message']!r}"
    )