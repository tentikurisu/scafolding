"""Evaluation harness spike.

Runs the full pipeline (LLM -> lambda -> API -> agent message) for each
scenario x behavior combination, N times. Prints a per-scenario Jaccard
and pass-rate table.

Useful when you swap in a real LLM and want to see drift surface.
"""

from __future__ import annotations

import asyncio

from repeatability_scaffold.behaviors.catalog import BEHAVIORS
from repeatability_scaffold.behaviors.expected_responses import matches_expected
from repeatability_scaffold.llm.evaluator import jaccard_similarity
from repeatability_scaffold.pipeline.api_registry import build_default_registry
from repeatability_scaffold.pipeline.execution_lambda import ExecutionLambda
from repeatability_scaffold.pipeline.llm_client import LLMClient
from tests.conftest import SCENARIOS


N_RUNS = 10


async def main() -> None:
    print("=== Evaluate spike ===\n")
    llm = LLMClient()
    registry = build_default_registry()
    lam = ExecutionLambda(llm, registry)

    rows: list[tuple[str, str, int, float, str]] = []

    for scenario in SCENARIOS:
        for behavior in BEHAVIORS:
            async def once():
                return await lam.handle(
                    prompt="describe " + scenario,
                    scenario=scenario,
                    behavior=behavior,
                )

            results = await asyncio.gather(*(once() for _ in range(N_RUNS)))

            # Agent message stability.
            messages = [r["agent_message"] for r in results]
            unique_messages = set(messages)
            message_jaccard = jaccard_similarity(messages)

            # Token-containment check against expected.
            pass_count = sum(
                1 for m in messages if matches_expected(m, scenario, behavior)[0]
            )

            rows.append(
                (scenario, behavior, pass_count, message_jaccard, str(len(unique_messages)))
            )

    print(f"{'scenario':<25} {'behavior':<20} {'passes':<8} {'jaccard':<10} {'unique':<8}")
    print("-" * 80)
    for scenario, behavior, passes, jacc, unique in rows:
        print(f"{scenario:<25} {behavior:<20} {passes}/{N_RUNS:<6} {jacc:<10.3f} {unique:<8}")


if __name__ == "__main__":
    asyncio.run(main())