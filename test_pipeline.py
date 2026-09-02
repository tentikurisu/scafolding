"""Repeatability tests: LLM and execution lambda must be deterministic.

Run each scenario N times; assert all runs produce identical output.
With MockLLM this should always hold; with a real LLM it surfaces drift.
"""

from __future__ import annotations

import asyncio

import pytest

from llm import validate_llm_response
from validators import jaccard


# === LLM repeatability ===============================================

@pytest.mark.parametrize("scenario", ["fetch_red", "check_17", "describe_pentagon"])
def test_llm_first_call_is_deterministic(scenario, llm, n_runs):
    async def once():
        return await llm.first_call("describe " + scenario, scenario)

    results = _run_n_async(lambda: once(), n_runs)
    first = results[0]
    assert all(r == first for r in results), (
        f"LLM decision drifted: first={first}, all={results}"
    )


@pytest.mark.parametrize("scenario", ["fetch_red", "check_17", "describe_pentagon"])
def test_llm_decision_schema_valid(scenario, llm, n_runs):
    async def once():
        return await llm.first_call("describe " + scenario, scenario)

    results = _run_n_async(lambda: once(), n_runs)
    for raw in results:
        parsed = validate_llm_response(raw)
        assert parsed.action
        assert parsed.target_api
        assert isinstance(parsed.params, dict)


@pytest.mark.parametrize("scenario", ["fetch_red", "check_17", "describe_pentagon"])
def test_llm_reasoning_similar_across_runs(scenario, llm, n_runs):
    """Jaccard >= 0.95 on reasoning text across N runs."""
    async def once():
        raw = await llm.first_call("describe " + scenario, scenario)
        return validate_llm_response(raw).reasoning

    reasonings = _run_n_async(once, n_runs)
    score = jaccard(reasonings)
    assert score >= 0.95, f"Jaccard {score:.3f} below 0.95 for {scenario!r}"


# === Lambda repeatability ============================================

@pytest.mark.parametrize("behavior", ["successful", "not_found", "api_500", "timeout"])
@pytest.mark.parametrize("scenario", ["fetch_red", "check_17", "describe_pentagon"])
def test_execution_lambda_deterministic(scenario, behavior, execution_lambda, n_runs):
    async def once():
        return await execution_lambda.handle(
            prompt="describe " + scenario,
            scenario=scenario,
            behavior=behavior,
        )

    results = _run_n_async(once, n_runs)
    first = results[0]
    drift = [r for r in results if r != first]
    assert not drift, (
        f"Lambda drifted for {scenario!r}/{behavior!r}: {len(drift)}/{n_runs} runs differed"
    )


@pytest.mark.parametrize("scenario", ["fetch_red", "check_17", "describe_pentagon"])
def test_agent_message_stable(scenario, execution_lambda, n_runs):
    async def once():
        return await execution_lambda.handle(
            prompt="describe " + scenario,
            scenario=scenario,
            behavior="successful",
        )

    results = _run_n_async(once, n_runs)
    messages = [r["agent_message"] for r in results]
    assert len(set(messages)) == 1, f"{scenario}: agent_message drifted: {set(messages)}"


def _run_n_async(coro_factory, n):
    """Drive an async callable N times from a sync test function."""
    async def runner():
        return [await coro_factory() for _ in range(n)]
    return asyncio.run(runner())