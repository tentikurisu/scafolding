"""Expected agent responses per (scenario, behavior) — token-containment model.

Validation rule:

- For each `(scenario, behavior)`, define the tokens that MUST appear in the
  agent_message. The check is plain substring matching, case-insensitive.
- Optionally, define GROUPS — alternative token combinations. If GROUPS is
  specified for a key, the response is valid if AT LEAST ONE group's tokens
  all appear in the response.

Examples (matching the user's mental model):

  "asking about the color red"      -> response contains "red"
  "asking about red, group 2"      -> response contains "red" AND "2"

Sources (highest priority first):
1. `scenarios[scenario].expectations` in repeatability.yaml
2. `scenarios[scenario].expectation_groups` in repeatability.yaml
3. Python defaults below (used if no config exists for that scenario)
"""

from __future__ import annotations

from typing import Iterable

from ..config import get_config, get_scenarios_config


def must_contain_all(text: str, tokens: Iterable[str]) -> bool:
    """True iff every token appears in `text` (case-insensitive substring)."""
    haystack = text.lower()
    return all(t.lower() in haystack for t in tokens)


def must_contain_group(text: str, groups: Iterable[Iterable[str]]) -> bool:
    """True iff at least one group has all its tokens present in `text`."""
    return any(must_contain_all(text, g) for g in groups)


# === Python defaults (used when no YAML config provides them) ========

_DEFAULT_EXPECTED_TOKENS: dict[tuple[str, str], list[str]] = {
    ("fetch_color_red", "successful"):       ["red", "#FF0000"],
    ("fetch_color_red", "empty"):            ["unavailable"],
    ("fetch_color_red", "not_found"):        ["not found"],
    ("fetch_color_red", "missing_field"):    ["red"],
    ("fetch_color_red", "malformed_payload"): ["unexpected"],
    ("fetch_color_red", "api_400"):          ["invalid request"],
    ("fetch_color_red", "api_401_403"):      ["access"],
    ("fetch_color_red", "api_500"):          ["service", "error"],
    ("fetch_color_red", "timeout"):          ["unavailable"],

    ("fetch_color_xyz", "successful"):       ["xyz"],
    ("fetch_color_xyz", "empty"):            ["unavailable"],
    ("fetch_color_xyz", "not_found"):        ["not found"],
    ("fetch_color_xyz", "missing_field"):    ["partial"],
    ("fetch_color_xyz", "malformed_payload"): ["unexpected"],
    ("fetch_color_xyz", "api_400"):          ["invalid request"],
    ("fetch_color_xyz", "api_401_403"):      ["access"],
    ("fetch_color_xyz", "api_500"):          ["service", "error"],
    ("fetch_color_xyz", "timeout"):          ["unavailable"],

    ("check_prime_17", "successful"):       ["17", "prime"],
    ("check_prime_17", "empty"):            ["unavailable"],
    ("check_prime_17", "not_found"):        ["not found"],
    ("check_prime_17", "missing_field"):    ["partial"],
    ("check_prime_17", "malformed_payload"): ["unexpected"],
    ("check_prime_17", "api_400"):          ["invalid request"],
    ("check_prime_17", "api_401_403"):      ["access"],
    ("check_prime_17", "api_500"):          ["service", "error"],
    ("check_prime_17", "timeout"):          ["unavailable"],

    ("check_negative_number", "successful"):       ["-7", "not"],
    ("check_negative_number", "empty"):            ["unavailable"],
    ("check_negative_number", "not_found"):        ["not found"],
    ("check_negative_number", "missing_field"):    ["partial"],
    ("check_negative_number", "malformed_payload"): ["unexpected"],
    ("check_negative_number", "api_400"):          ["invalid request"],
    ("check_negative_number", "api_401_403"):      ["access"],
    ("check_negative_number", "api_500"):          ["service", "error"],
    ("check_negative_number", "timeout"):          ["unavailable"],

    ("describe_pentagon", "successful"):       ["pentagon"],
    ("describe_pentagon", "empty"):            ["unavailable"],
    ("describe_pentagon", "not_found"):        ["not found"],
    ("describe_pentagon", "missing_field"):    ["partial"],
    ("describe_pentagon", "malformed_payload"): ["unexpected"],
    ("describe_pentagon", "api_400"):          ["invalid request"],
    ("describe_pentagon", "api_401_403"):      ["access"],
    ("describe_pentagon", "api_500"):          ["service", "error"],
    ("describe_pentagon", "timeout"):          ["unavailable"],

    ("describe_unknown_shape", "successful"):       ["hexaflexagon"],
    ("describe_unknown_shape", "empty"):            ["unavailable"],
    ("describe_unknown_shape", "not_found"):        ["not found"],
    ("describe_unknown_shape", "missing_field"):    ["partial"],
    ("describe_unknown_shape", "malformed_payload"): ["unexpected"],
    ("describe_unknown_shape", "api_400"):          ["invalid request"],
    ("describe_unknown_shape", "api_401_403"):      ["access"],
    ("describe_unknown_shape", "api_500"):          ["service", "error"],
    ("describe_unknown_shape", "timeout"):          ["unavailable"],
}


_DEFAULT_EXPECTED_GROUPS: dict[tuple[str, str], list[list[str]]] = {
    ("describe_pentagon", "successful"): [
        ["pentagon", "five"],
        ["pentagon", "polygon"],
        ["pentagon", "side"],
    ],
    ("describe_unknown_shape", "successful"): [
        ["hexaflexagon"],
        ["flexing", "shape"],
    ],
    ("check_negative_number", "successful"): [
        ["-7", "not"],
        ["-7", "isn't"],
        ["-7", "is not"],
    ],
}


# === Merge config + defaults =========================================

def _build_expected() -> tuple[dict[tuple[str, str], list[str]], dict[tuple[str, str], list[list[str]]]]:
    tokens: dict[tuple[str, str], list[str]] = {}
    groups: dict[tuple[str, str], list[list[str]]] = {}

    scenarios_cfg = get_scenarios_config()
    for scenario_name, scenario_cfg in scenarios_cfg.items():
        if not isinstance(scenario_cfg, dict):
            continue
        for behavior, behavior_tokens in scenario_cfg.get("expectations", {}).items():
            tokens[(scenario_name, behavior)] = list(behavior_tokens)
        for behavior, group_list in scenario_cfg.get("expectation_groups", {}).items():
            groups[(scenario_name, behavior)] = [list(g) for g in group_list]

    # Fill in gaps from defaults
    for k, v in _DEFAULT_EXPECTED_TOKENS.items():
        tokens.setdefault(k, v)
    for k, v in _DEFAULT_EXPECTED_GROUPS.items():
        groups.setdefault(k, v)

    return tokens, groups


EXPECTED_TOKENS: dict[tuple[str, str], list[str]]
EXPECTED_GROUPS: dict[tuple[str, str], list[list[str]]]
EXPECTED_TOKENS, EXPECTED_GROUPS = _build_expected()


# === Public API ======================================================

def matches_expected(
    text: str,
    scenario: str,
    behavior: str,
) -> tuple[bool, str]:
    """Return (ok, reason). If GROUPS is defined for the key, at least one
    group must match. Otherwise, all EXPECTED_TOKENS must appear.
    """
    key = (scenario, behavior)
    if key in EXPECTED_GROUPS:
        ok = must_contain_group(text, EXPECTED_GROUPS[key])
        return ok, "group match" if ok else f"no group matched: {EXPECTED_GROUPS[key]}"
    tokens = EXPECTED_TOKENS.get(key)
    if tokens is None:
        return False, f"no expected tokens for {key!r}"
    ok = must_contain_all(text, tokens)
    return ok, "all tokens present" if ok else f"missing tokens: {tokens}"


def tokens_for(scenario: str, behavior: str) -> list[str]:
    return list(EXPECTED_TOKENS.get((scenario, behavior), []))


def groups_for(scenario: str, behavior: str) -> list[list[str]]:
    return [list(g) for g in EXPECTED_GROUPS.get((scenario, behavior), [])]


def reload_from_config() -> None:
    """Re-read expectations from config."""
    global EXPECTED_TOKENS, EXPECTED_GROUPS
    EXPECTED_TOKENS, EXPECTED_GROUPS = _build_expected()


def scenario_input(scenario: str) -> dict | None:
    """Return the YAML config block for a scenario (prompt, params, etc.)."""
    return get_scenarios_config().get(scenario)