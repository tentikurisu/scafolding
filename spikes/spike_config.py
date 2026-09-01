"""Config loader spike.

Prints the loaded `repeatability.yaml` config (or notes its absence).
Use this to verify your config edits are being picked up.

Usage:
    python -m spikes.spike_config
    REPEATABILITY_CONFIG=/path/to/other.yaml python -m spikes.spike_config
"""

from __future__ import annotations

import json

from repeatability_scaffold.config import (
    config_path,
    get_apis_config,
    get_behaviors_config,
    get_llm_config,
    get_scenarios_config,
    get_tests_config,
    has_config,
)


def main() -> None:
    print("=== Config spike ===\n")
    print(f"Config loaded: {has_config()}")
    print(f"Config path:   {config_path()}\n")

    print("--- llm ---")
    print(json.dumps(get_llm_config(), indent=2))
    print()

    print("--- apis ---")
    print(json.dumps(get_apis_config(), indent=2))
    print()

    print("--- behaviors ---")
    print(json.dumps(get_behaviors_config(), indent=2))
    print()

    print("--- tests ---")
    print(json.dumps(get_tests_config(), indent=2))
    print()

    scenarios = get_scenarios_config()
    print(f"--- scenarios ({len(scenarios)}) ---")
    for name, cfg in scenarios.items():
        print(f"  {name}:")
        print(f"    prompt:     {cfg.get('prompt')!r}")
        print(f"    target_api: {cfg.get('target_api')!r}")
        print(f"    params:     {cfg.get('params')!r}")
        print(f"    expectations: {list((cfg.get('expectations') or {}).keys())}")
        if cfg.get("expectation_groups"):
            print(f"    groups:       {list(cfg['expectation_groups'].keys())}")


if __name__ == "__main__":
    main()