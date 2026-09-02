"""Mock LLM provider.

This is a MOCK — deterministic, no network, used for tests without a
real LLM. To use a real LLM (Bedrock, OpenAI, etc.), see SWAP_GUIDE.md
and real_examples.py for the patterns.

Two stages:
  - first_call(prompt, scenario) -> decision dict (action, target_api, params, reasoning)
  - second_call(scenario, behavior, api_response, api_error) -> agent_message string

Both are deterministic by key. Edit STUB_RESPONSES and AGENT_MESSAGES
to match your scenarios and expected messages.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class LLMResponse(BaseModel):
    """LLM decision schema. `extra="ignore"` is forgiving."""
    model_config = ConfigDict(extra="ignore")
    action: str = ""
    target_api: str = ""
    params: dict[str, Any] = {}
    reasoning: str = ""


def validate_llm_response(raw: dict) -> LLMResponse:
    return LLMResponse.model_validate(raw)


# === Stub data ========================================================
# Edit these for your domain.

STUB_RESPONSES: dict[str, dict[str, Any]] = {
    "fetch_red": {
        "action": "fetch",
        "target_api": "colors",
        "params": {"name": "red"},
        "reasoning": "Looking up color information for red.",
    },
    "check_17": {
        "action": "check",
        "target_api": "numbers",
        "params": {"n": 17, "property": "is_prime"},
        "reasoning": "Checking whether 17 is prime.",
    },
    "describe_pentagon": {
        "action": "describe",
        "target_api": "shapes",
        "params": {"name": "pentagon"},
        "reasoning": "Describing the pentagon.",
    },
}


AGENT_MESSAGES: dict[tuple[str, str], str] = {
    # fetch_red
    ("fetch_red", "successful"):       "Red has hex #FF0000 and complementary cyan.",
    ("fetch_red", "empty"):            "Color info unavailable.",
    ("fetch_red", "not_found"):        "Record not found for that color.",
    ("fetch_red", "missing_field"):    "Red is available, other fields missing.",
    ("fetch_red", "malformed_payload"): "The data was unexpected.",
    ("fetch_red", "api_400"):          "Invalid request.",
    ("fetch_red", "api_401_403"):      "Access denied.",
    ("fetch_red", "api_500"):          "Service error.",
    ("fetch_red", "timeout"):          "Service unavailable.",

    # check_17
    ("check_17", "successful"):       "Yes, 17 is prime.",
    ("check_17", "empty"):            "Number info unavailable.",
    ("check_17", "not_found"):        "Properties not found.",
    ("check_17", "missing_field"):    "Partial info about 17.",
    ("check_17", "malformed_payload"): "The data was unexpected.",
    ("check_17", "api_400"):          "Invalid request.",
    ("check_17", "api_401_403"):      "Access denied.",
    ("check_17", "api_500"):          "Service error.",
    ("check_17", "timeout"):          "Service unavailable.",

    # describe_pentagon
    ("describe_pentagon", "successful"):       "A pentagon has 5 sides.",
    ("describe_pentagon", "empty"):            "Shape info unavailable.",
    ("describe_pentagon", "not_found"):        "Record not found.",
    ("describe_pentagon", "missing_field"):    "Partial info about pentagon.",
    ("describe_pentagon", "malformed_payload"): "The data was unexpected.",
    ("describe_pentagon", "api_400"):          "Invalid request.",
    ("describe_pentagon", "api_401_403"):      "Access denied.",
    ("describe_pentagon", "api_500"):          "Service error.",
    ("describe_pentagon", "timeout"):          "Service unavailable.",
}


# === Mock provider ===================================================

class MockLLM:
    """Mock LLM provider. Deterministic, no network.

    Use this in tests when you don't have (or don't want to use) a real LLM.
    Replace with your own class (e.g., BedrockLLM) to swap in a real one.
    See SWAP_GUIDE.md and real_examples.py.
    """

    async def first_call(self, prompt: str, scenario: str) -> dict[str, Any]:
        if scenario not in STUB_RESPONSES:
            raise KeyError(f"Unknown scenario: {scenario!r}")
        return dict(STUB_RESPONSES[scenario])

    async def second_call(
        self,
        scenario: str,
        behavior: str,
        api_response: dict | None,
        api_error: str | None,
    ) -> str:
        key = (scenario, behavior)
        if key not in AGENT_MESSAGES:
            raise KeyError(f"No agent message for {key!r}")
        return AGENT_MESSAGES[key]