"""LLM-stage repeatability.

For each scenario, the LLM stub must return an identical decision dict across
N runs, and the LLM's free-text fields must achieve Jaccard ≥ threshold
(1.0 with deterministic stubs).
"""

from __future__ import annotations

import json

import pytest

from repeatability_scaffold.llm.evaluator import (
    assert_concise,
    free_text_fields,
    jaccard_similarity,
    validate_llm_response,
)
from repeatability_scaffold.llm.schemas import LLMResponse
from tests.conftest import SCENARIOS, run_n_times_async


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_decision_is_deterministic(scenario, llm_client):
    """N runs of the LLM's first call must produce identical decisions."""
    async def once():
        return await llm_client.ask("describe " + scenario, scenario)

    results = await run_n_times_async(once, n=10)
    first = results[0]
    drift = [i for i, r in enumerate(results) if r != first]
    assert not drift, (
        f"LLM decision drifted across runs for {scenario!r} at indices {drift}\n"
        f"  first: {first}\n"
        f"  drifted: {[results[i] for i in drift]}"
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_decision_schema_valid(scenario, llm_client, report_writer):
    """Every run's decision must parse as LLMResponse and be well-formed."""
    async def once():
        return await llm_client.ask("describe " + scenario, scenario)

    results = await run_n_times_async(once, n=10)

    parse_failures: list[int] = []
    well_formed_failures: list[int] = []
    for i, raw in enumerate(results):
        try:
            parsed = validate_llm_response(raw)
        except Exception as exc:
            parse_failures.append(i)
            continue
        if not parsed.is_well_formed():
            well_formed_failures.append(i)

    assert not parse_failures, f"Schema parse failures at indices {parse_failures}"
    assert not well_formed_failures, (
        f"LLM response not well-formed at indices {well_formed_failures}"
    )

    report_writer(scenario=scenario, stage="llm_first_call", passes=10, total=10, pass_rate=1.0)


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_free_text_jaccard_meets_threshold(
    scenario, llm_client, jaccard_threshold, report_writer
):
    """Free-text Jaccard across N runs must be >= threshold."""
    async def once():
        return await llm_client.ask("describe " + scenario, scenario)

    results = await run_n_times_async(once, n=10)
    parsed = [validate_llm_response(r) for r in results]
    score = jaccard_similarity(parsed)

    report_writer(
        scenario=scenario,
        stage="llm_first_call_jaccard",
        jaccard=round(score, 4),
        threshold=jaccard_threshold,
    )

    assert score >= jaccard_threshold, (
        f"Jaccard {score:.3f} below threshold {jaccard_threshold} for {scenario!r}\n"
        f"  free-text samples: {[free_text_fields(p) for p in parsed[:3]]}"
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_llm_response_is_concise(scenario, llm_client):
    """Every run's reasoning must be within length bounds."""
    async def once():
        return await llm_client.ask("describe " + scenario, scenario)

    results = await run_n_times_async(once, n=10)
    for raw in results:
        parsed = validate_llm_response(raw)
        assert_concise(parsed)


async def test_llm_first_call_n_minus_one_drift_detection(scenario_loop=SCENARIOS):
    """Sanity check: any pairwise drift in N-1 of N runs surfaces as a failure.

    Implemented as a manual loop over scenarios to avoid extra parametrization.
    """
    from repeatability_scaffold.pipeline.llm_client import LLMClient

    client = LLMClient()
    for scenario in scenario_loop:
        results = await run_n_times_async(
            lambda s=scenario: client.ask("describe " + s, s), n=10
        )
        unique = {json.dumps(r, sort_keys=True) for r in results}
        assert len(unique) == 1, f"{scenario}: produced {len(unique)} unique responses"