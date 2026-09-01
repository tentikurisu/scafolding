"""API send/receive spike.

Demonstrates calling each stubbed API with each of the 9 placeholder
behaviors. Useful for visually inspecting what each behavior returns.
"""

from __future__ import annotations

import asyncio
import json
import traceback

from repeatability_scaffold.behaviors.catalog import BEHAVIORS
from repeatability_scaffold.pipeline.api_registry import build_default_registry
from repeatability_scaffold.goldens.api_goldens import golden_for


async def main() -> None:
    print("=== API send/receive spike ===\n")
    registry = build_default_registry()

    for api_name in registry.names():
        client = registry.get(api_name)
        print(f"### API: {api_name}\n")
        for behavior in BEHAVIORS:
            print(f"  -- behavior: {behavior} --")
            try:
                result = await client.call(params={}, behavior=behavior)
                print(f"    payload: {json.dumps(result, default=str)}")
                golden = golden_for(api_name, behavior)
                if golden is not None:
                    print(f"    golden:  {json.dumps(golden, default=str)}")
                else:
                    print(f"    golden:  None")
            except Exception as exc:
                print(f"    raised: {type(exc).__name__}: {exc}")
            print()
        print()


if __name__ == "__main__":
    asyncio.run(main())