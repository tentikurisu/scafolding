"""LLM conciseness evaluation.

A concise LLM response is:

- Well-formed (required fields present, types correct).
- Bounded in length (no runaway free text).
- Free of extraneous meta-fields.
- Has a non-empty `reasoning` field with semantic content (not just boilerplate).
"""

from __future__ import annotations

import pytest

from repeatability_scaffold.llm.evaluator import (
    assert_concise,
    validate_llm_response,
)
from tests.conftest import SCENARIOS, run_n_times_async


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_response_required_fields_present(scenario, llm_client):
    async def once():
        return await llm_client.ask("describe " + scenario, scenario)

    results = await run_n_times_async(once, n=10)
    for raw in results:
        parsed = validate_llm_response(raw)
        assert_concise(parsed)


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_response_reasoning_within_bounds(scenario, llm_client):
    async def once():
        return await llm_client.ask("describe " + scenario, scenario)

    results = await run_n_times_async(once, n=10)
    for raw in results:
        parsed = validate_llm_response(raw)
        assert 0 < len(parsed.reasoning) <= 500, (
            f"{scenario}: reasoning length {len(parsed.reasoning)} out of bounds"
        )


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_response_params_is_dict(scenario, llm_client):
    async def once():
        return await llm_client.ask("describe " + scenario, scenario)

    results = await run_n_times_async(once, n=10)
    for raw in results:
        parsed = validate_llm_response(raw)
        assert isinstance(parsed.params, dict)
        assert len(parsed.params) >= 1, (
            f"{scenario}: params is empty dict"
        )


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_response_agent_message_within_bounds(scenario, execution_lambda):
    """The user-facing agent_message should be reasonable length too."""
    async def once():
        return await execution_lambda.handle(
            prompt="describe " + scenario,
            scenario=scenario,
            behavior="successful",
        )

    results = await run_n_times_async(once, n=10)
    for r in results:
        msg = r["agent_message"]
        assert 0 < len(msg) <= 500, (
            f"{scenario}: agent_message length {len(msg)} out of bounds"
        )


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_response_no_invented_apis(scenario, llm_client):
    """LLM should never invent an API outside the registered set."""
    from repeatability_scaffold.pipeline.api_registry import build_default_registry

    async def once():
        return await llm_client.ask("describe " + scenario, scenario)

    results = await run_n_times_async(once, n=10)
    registry = build_default_registry()
    for raw in results:
        parsed = validate_llm_response(raw)
        assert parsed.target_api in registry, (
            f"{scenario}: LLM invented unregistered API {parsed.target_api!r}"
        )