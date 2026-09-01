"""Execution-lambda repeatability.

The lambda is deterministic with stubbed inputs. Across N runs of the same
prompt + scenario + behavior, the full output dict must be identical.
"""

from __future__ import annotations

import pytest

from repeatability_scaffold.behaviors.catalog import BEHAVIORS
from tests.conftest import SCENARIOS, run_n_times_async


@pytest.mark.parametrize("scenario", SCENARIOS)
@pytest.mark.parametrize("behavior", BEHAVIORS)
async def test_execution_lambda_deterministic(scenario, behavior, execution_lambda, report_writer):
    """Same prompt + scenario + behavior -> identical output N times."""
    async def once():
        return await execution_lambda.handle(
            prompt="describe " + scenario,
            scenario=scenario,
            behavior=behavior,
        )

    results = await run_n_times_async(once, n=10)
    first = results[0]
    drift = [i for i, r in enumerate(results) if r != first]

    report_writer(
        scenario=scenario,
        behavior=behavior,
        stage="execution_lambda",
        passes=10 - len(drift),
        total=10,
        pass_rate=(10 - len(drift)) / 10,
    )

    assert not drift, (
        f"Execution lambda drifted for {scenario!r}/{behavior!r} at indices {drift}\n"
        f"  first: {first}\n"
        f"  drifted: {[results[i] for i in drift[:3]]}"
    )


@pytest.mark.parametrize("scenario", SCENARIOS)
async def test_execution_lambda_agent_message_stable(scenario, execution_lambda):
    """The user-facing agent_message is identical across N runs."""
    async def once():
        return await execution_lambda.handle(
            prompt="describe " + scenario,
            scenario=scenario,
            behavior="successful",
        )

    results = await run_n_times_async(once, n=10)
    messages = [r["agent_message"] for r in results]
    assert len(set(messages)) == 1, (
        f"{scenario}: agent_message drifted: {set(messages)}"
    )