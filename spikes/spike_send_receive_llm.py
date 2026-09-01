"""LLM send/receive spike.

Demonstrates the two LLM call stages with the stub provider. Useful for
sanity-checking that the LLM interface returns well-formed dicts.
"""

from __future__ import annotations

import asyncio
import json

from repeatability_scaffold.pipeline.llm_client import LLMClient
from repeatability_scaffold.llm.stub_provider import STUB_RESPONSES


async def main() -> None:
    print("=== LLM send/receive spike ===\n")
    client = LLMClient()

    print(f"Known scenarios: {list(STUB_RESPONSES.keys())}\n")

    for scenario in STUB_RESPONSES:
        print(f"--- Scenario: {scenario} ---")
        raw = await client.ask("describe " + scenario, scenario)
        print("First call (LLM decision):")
        print(json.dumps(raw, indent=2))

        msg = await client.generate_agent_message(
            scenario=scenario,
            behavior="successful",
            api_response={"placeholder": True},
            api_error=None,
        )
        print("Second call (agent message):")
        print(f"  {msg!r}\n")


if __name__ == "__main__":
    asyncio.run(main())