"""Behavior matrix: agent_message must contain expected tokens per (scenario, behavior).

Per (scenario, behavior) the lambda is run N=10 times; every agent_message
must contain all tokens listed in EXPECTED_TOKENS (case-insensitive substring).

Plus per-API semantic contracts and error behavior propagation.
"""

from __future__ import annotations

import asyncio

import pytest

from validators import contains_all


# === Token matrix ====================================================

@pytest.mark.parametrize("behavior", [
    "successful", "empty", "not_found", "missing_field", "malformed_payload",
    "api_400", "api_401_403", "api_500", "timeout",
])
@pytest.mark.parametrize("scenario", ["fetch_red", "check_17", "describe_pentagon"])
def test_agent_message_contains_expected_tokens(
    scenario, behavior, execution_lambda, expected_tokens, n_runs,
):
    tokens = expected_tokens.get((scenario, behavior), [])
    assert tokens, f"No expected tokens configured for {(scenario, behavior)}"

    async def once():
        return await execution_lambda.handle(
            prompt="describe " + scenario, scenario=scenario, behavior=behavior,
        )

    results = _run_n_async(once, n_runs)
    failures = []
    for r in results:
        msg = r["agent_message"]
        if not contains_all(msg, tokens):
            failures.append(msg)

    assert not failures, (
        f"{scenario}/{behavior}: {len(failures)}/{n_runs} runs missing tokens {tokens}\n"
        f"  sample failures: {failures[:3]}"
    )


# === Semantic contracts ===============================================

@pytest.mark.parametrize("behavior", [
    "successful", "empty", "not_found", "missing_field", "malformed_payload",
    "api_400", "api_401_403", "api_500", "timeout",
])
def test_colors_contract(behavior, execution_lambda):
    """Per-behavior contracts for the colors API."""
    async def run():
        return (await execution_lambda.handle(
            prompt="describe red", scenario="fetch_red", behavior=behavior,
        ))["agent_message"]
    msg = asyncio.run(run()).lower()

    if behavior == "successful":
        assert "red" in msg
    elif behavior == "empty":
        assert "#" not in msg
    elif behavior == "not_found":
        for invented in ["red", "blue", "green"]:
            assert invented not in msg.split()
    elif behavior == "missing_field":
        assert "red" in msg
    elif behavior == "malformed_payload":
        assert "unexpected" in msg
    elif behavior == "api_400":
        assert "invalid" in msg
    elif behavior == "api_401_403":
        assert "access" in msg
    elif behavior == "api_500":
        assert "error" in msg
    elif behavior == "timeout":
        assert "unavailable" in msg


@pytest.mark.parametrize("behavior", ["api_400", "api_401_403", "api_500", "timeout"])
def test_error_behaviors_propagate(behavior, apis):
    """Error behaviors must raise (so the lambda can capture the failure)."""
    client = apis["colors"]
    with pytest.raises(Exception):
        asyncio.run(client.call(params={}, behavior=behavior))


def _run_n_async(coro_factory, n):
    async def runner():
        return [await coro_factory() for _ in range(n)]
    return asyncio.run(runner())