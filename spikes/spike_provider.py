"""Provider dispatch spike.

Demonstrates that the same pipeline code runs against any registered
provider. By default uses stub; switch with LLM_PROVIDER env var or
the --provider CLI flag.

Useful for sanity-checking that a real provider (e.g., bedrock) is
wired up correctly: the stub returns instantly and deterministically,
so any deviation points at the provider integration.

Usage:
    python -m spikes.spike_provider
    python -m spikes.spike_provider --provider bedrock
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from repeatability_scaffold.llm.providers import available_providers
from repeatability_scaffold.pipeline.api_registry import build_default_registry
from repeatability_scaffold.pipeline.execution_lambda import ExecutionLambda
from repeatability_scaffold.pipeline.llm_client import LLMClient


async def main(provider: str) -> None:
    print(f"=== Provider spike (provider={provider!r}) ===\n")
    print(f"Available providers: {available_providers()}\n")

    client = LLMClient(provider=provider)
    registry = build_default_registry()
    lam = ExecutionLambda(client, registry)

    scenario = "fetch_color_red"
    behavior = "successful"

    print(f"Running scenario={scenario!r}, behavior={behavior!r} x3...\n")
    for i in range(3):
        result = await lam.handle(
            prompt="describe " + scenario,
            scenario=scenario,
            behavior=behavior,
        )
        print(f"--- run {i+1} ---")
        print(f"  llm_decision: {json.dumps(result['llm_decision'], default=str)}")
        print(f"  api_response: {json.dumps(result['api_response'], default=str)}")
        print(f"  api_error:    {result['api_error']!r}")
        print(f"  agent_message: {result['agent_message']!r}")
        print()


def cli() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        default=os.environ.get("LLM_PROVIDER", "stub"),
        choices=available_providers(),
        help="LLM provider to use",
    )
    args = parser.parse_args()
    asyncio.run(main(args.provider))


if __name__ == "__main__":
    cli()