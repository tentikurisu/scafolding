"""Deterministic LLM stubs.

Two stages of LLM calls happen in the pipeline:

1. **First call**: user prompt -> decision (action, target_api, params, reasoning).
2. **Second call**: API response/error -> final agent message.

Both stages are stubbed. The stubs are *deterministic*: the same `(scenario)`
returns the same first-call dict; the same `(scenario, behavior)` returns the
same agent message every time.

Stub data is loaded from `repeatability.yaml` if present (under
`scenarios.<name>.stub_response` and `scenarios.<name>.agent_messages`).
Python defaults are used when no YAML entry exists for a given key.

Swap-in point for a real LLM: replace `StubProvider` with a real provider
(e.g. `BedrockProvider`). Pipeline code does not change.
"""

from __future__ import annotations

from typing import Any

from ..config import get_scenarios_config


# === Python defaults (used when YAML doesn't supply an entry) ========

_DEFAULT_STUB_RESPONSES: dict[str, dict[str, Any]] = {
    "fetch_color_red": {
        "action": "fetch",
        "target_api": "colors",
        "params": {"name": "red"},
        "reasoning": "Looking up color information for red as requested.",
    },
    "fetch_color_xyz": {
        "action": "fetch",
        "target_api": "colors",
        "params": {"name": "xyz"},
        "reasoning": "Looking up color information for xyz.",
    },
    "check_prime_17": {
        "action": "check",
        "target_api": "numbers",
        "params": {"n": 17, "property": "is_prime"},
        "reasoning": "Checking whether 17 is a prime number.",
    },
    "check_negative_number": {
        "action": "check",
        "target_api": "numbers",
        "params": {"n": -7, "property": "is_prime"},
        "reasoning": "Checking whether -7 is a prime number.",
    },
    "describe_pentagon": {
        "action": "describe",
        "target_api": "shapes",
        "params": {"name": "pentagon"},
        "reasoning": "Describing the pentagon shape.",
    },
    "describe_unknown_shape": {
        "action": "describe",
        "target_api": "shapes",
        "params": {"name": "hexaflexagon"},
        "reasoning": "Describing the hexaflexagon shape.",
    },
}


_DEFAULT_AGENT_MESSAGES: dict[tuple[str, str], str] = {
    # fetch_color_red
    ("fetch_color_red", "successful"): "Red has hex code #FF0000 and complementary cyan.",
    ("fetch_color_red", "empty"): "Color information is currently unavailable.",
    ("fetch_color_red", "not_found"): "No record was not found for that color.",
    ("fetch_color_red", "missing_field"): "Red is available, but other fields were missing.",
    ("fetch_color_red", "malformed_payload"): "The data I received was unexpected and could not be parsed.",
    ("fetch_color_red", "api_400"): "Invalid request. Please check the color name.",
    ("fetch_color_red", "api_401_403"): "I don't have access to the colors service right now.",
    ("fetch_color_red", "api_500"): "The colors service is reporting a service error. Please try again later.",
    ("fetch_color_red", "timeout"): "The colors service is unavailable. Please try again.",

    # fetch_color_xyz
    ("fetch_color_xyz", "successful"): "Xyz has hex code #ABCDEF and complementary color.",
    ("fetch_color_xyz", "empty"): "Color information is currently unavailable.",
    ("fetch_color_xyz", "not_found"): "No record was not found for that color.",
    ("fetch_color_xyz", "missing_field"): "I have partial information, but other fields were missing.",
    ("fetch_color_xyz", "malformed_payload"): "The data I received was unexpected and could not be parsed.",
    ("fetch_color_xyz", "api_400"): "Invalid request. Please check the color name.",
    ("fetch_color_xyz", "api_401_403"): "I don't have access to the colors service right now.",
    ("fetch_color_xyz", "api_500"): "The colors service is reporting a service error. Please try again later.",
    ("fetch_color_xyz", "timeout"): "The colors service is unavailable. Please try again.",

    # check_prime_17
    ("check_prime_17", "successful"): "Yes, 17 is a prime number.",
    ("check_prime_17", "empty"): "Number information is currently unavailable.",
    ("check_prime_17", "not_found"): "Properties not found for that number.",
    ("check_prime_17", "missing_field"): "I have partial information about 17.",
    ("check_prime_17", "malformed_payload"): "The data I received was unexpected and could not be parsed.",
    ("check_prime_17", "api_400"): "Invalid request. Please check the number.",
    ("check_prime_17", "api_401_403"): "I don't have access to the numbers service right now.",
    ("check_prime_17", "api_500"): "The numbers service is reporting a service error. Please try again later.",
    ("check_prime_17", "timeout"): "The numbers service is unavailable. Please try again.",

    # check_negative_number
    ("check_negative_number", "successful"): "By convention, -7 is not prime.",
    ("check_negative_number", "empty"): "Number information is currently unavailable.",
    ("check_negative_number", "not_found"): "Properties not found for that number.",
    ("check_negative_number", "missing_field"): "I have partial information about -7.",
    ("check_negative_number", "malformed_payload"): "The data I received was unexpected and could not be parsed.",
    ("check_negative_number", "api_400"): "Invalid request. Please check the number.",
    ("check_negative_number", "api_401_403"): "I don't have access to the numbers service right now.",
    ("check_negative_number", "api_500"): "The numbers service is reporting a service error. Please try again later.",
    ("check_negative_number", "timeout"): "The numbers service is unavailable. Please try again.",

    # describe_pentagon
    ("describe_pentagon", "successful"): "A pentagon is a five-sided polygon.",
    ("describe_pentagon", "empty"): "Shape information is currently unavailable.",
    ("describe_pentagon", "not_found"): "No record was not found for that shape.",
    ("describe_pentagon", "missing_field"): "I have partial information about the pentagon.",
    ("describe_pentagon", "malformed_payload"): "The data I received was unexpected and could not be parsed.",
    ("describe_pentagon", "api_400"): "Invalid request. Please check the shape name.",
    ("describe_pentagon", "api_401_403"): "I don't have access to the shapes service right now.",
    ("describe_pentagon", "api_500"): "The shapes service is reporting a service error. Please try again later.",
    ("describe_pentagon", "timeout"): "The shapes service is unavailable. Please try again.",

    # describe_unknown_shape
    ("describe_unknown_shape", "successful"): "A hexaflexagon is an unusual flexing shape.",
    ("describe_unknown_shape", "empty"): "Shape information is currently unavailable.",
    ("describe_unknown_shape", "not_found"): "No record was not found for that shape.",
    ("describe_unknown_shape", "missing_field"): "I have partial information about that shape.",
    ("describe_unknown_shape", "malformed_payload"): "The data I received was unexpected and could not be parsed.",
    ("describe_unknown_shape", "api_400"): "Invalid request. Please check the shape name.",
    ("describe_unknown_shape", "api_401_403"): "I don't have access to the shapes service right now.",
    ("describe_unknown_shape", "api_500"): "The shapes service is reporting a service error. Please try again later.",
    ("describe_unknown_shape", "timeout"): "The shapes service is unavailable. Please try again.",
}


# === Merge config + defaults =========================================

def _build_stub_data() -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], str]]:
    responses: dict[str, dict[str, Any]] = {}
    messages: dict[tuple[str, str], str] = {}

    scenarios_cfg = get_scenarios_config()
    for scenario_name, scenario_cfg in scenarios_cfg.items():
        if not isinstance(scenario_cfg, dict):
            continue
        stub = scenario_cfg.get("stub_response")
        if isinstance(stub, dict):
            responses[scenario_name] = dict(stub)
        for behavior, msg in scenario_cfg.get("agent_messages", {}).items():
            messages[(scenario_name, behavior)] = str(msg)

    for k, v in _DEFAULT_STUB_RESPONSES.items():
        responses.setdefault(k, v)
    for k, v in _DEFAULT_AGENT_MESSAGES.items():
        messages.setdefault(k, v)

    return responses, messages


STUB_RESPONSES: dict[str, dict[str, Any]]
AGENT_MESSAGES: dict[tuple[str, str], str]
STUB_RESPONSES, AGENT_MESSAGES = _build_stub_data()


# === Provider implementation =========================================

def stub_first_call(prompt: str, scenario: str) -> dict[str, Any]:
    """First LLM call. Deterministic by scenario."""
    if scenario not in STUB_RESPONSES:
        raise KeyError(f"Unknown scenario: {scenario!r}")
    return dict(STUB_RESPONSES[scenario])


def stub_second_call(
    scenario: str,
    behavior: str,
    api_response: dict | None,
    api_error: str | None,
) -> str:
    """Second LLM call. Deterministic by (scenario, behavior)."""
    key = (scenario, behavior)
    if key not in AGENT_MESSAGES:
        raise KeyError(f"No agent message stub for {key!r}")
    return AGENT_MESSAGES[key]


class StubProvider:
    """Deterministic LLM provider. Default for tests."""

    async def first_call(self, prompt: str, scenario: str) -> dict[str, Any]:
        return stub_first_call(prompt, scenario)

    async def second_call(
        self,
        scenario: str,
        behavior: str,
        api_response: dict | None,
        api_error: str | None,
    ) -> str:
        return stub_second_call(scenario, behavior, api_response, api_error)


def reload_from_config() -> None:
    """Re-read stub data from config."""
    global STUB_RESPONSES, AGENT_MESSAGES
    STUB_RESPONSES, AGENT_MESSAGES = _build_stub_data()