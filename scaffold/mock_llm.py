"""MockLLM — deterministic local LLM stub.

Used by LocalMockSystem. Edit STUB_RESPONSES and AGENT_MESSAGES to add
scenarios. Production code should never import this.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class LLMResponse(BaseModel):
    """Generic LLM decision schema. `extra="ignore"` is forgiving."""

    model_config = ConfigDict(extra="ignore")
    action: str = ""
    target_api: str = ""
    params: dict[str, Any] = {}
    reasoning: str = ""


def validate_llm_response(raw: dict) -> LLMResponse:
    return LLMResponse.model_validate(raw)


# === Stub data — keyed by (scenario_name) and (scenario_name, behavior) ===

STUB_RESPONSES: dict[str, dict[str, Any]] = {
    "fetch_red": {
        "action": "fetch", "target_api": "colors", "params": {"name": "red"},
        "reasoning": "Looking up color red.",
    },
    "check_17": {
        "action": "check", "target_api": "numbers", "params": {"n": 17},
        "reasoning": "Checking 17.",
    },
    "describe_pentagon": {
        "action": "describe", "target_api": "shapes", "params": {"name": "pentagon"},
        "reasoning": "Describing pentagon.",
    },
    "fetch_red_not_found": {
        "action": "fetch", "target_api": "colors", "params": {"name": "xyz_not_a_real_color"},
        "reasoning": "Looking up unknown color.",
    },
    "fetch_red_empty": {
        "action": "fetch", "target_api": "colors", "params": {},
        "reasoning": "Empty lookup.",
    },
    "fetch_red_api_400": {
        "action": "fetch", "target_api": "colors", "params": {"name": "red"},
        "reasoning": "Will trigger 400.",
    },
    "fetch_red_api_500": {
        "action": "fetch", "target_api": "colors", "params": {"name": "red"},
        "reasoning": "Will trigger 500.",
    },
    "fetch_red_timeout": {
        "action": "fetch", "target_api": "colors", "params": {"name": "red"},
        "reasoning": "Will timeout.",
    },
    "fetch_red_malformed": {
        "action": "fetch", "target_api": "colors", "params": {"name": "red"},
        "reasoning": "Server returns corrupt payload.",
    },
}


AGENT_MESSAGES: dict[tuple[str, str], str] = {
    # fetch_red (successful)
    ("fetch_red", "successful"):         "Red has hex code #FF0000 and complementary cyan.",
    ("fetch_red", "not_found"):          "Color not found in the database.",
    ("fetch_red", "empty"):              "Color information is currently unavailable.",
    ("fetch_red", "api_400"):            "Invalid request. Please check the color name.",
    ("fetch_red", "api_401_403"):        "Access denied. Please check your credentials.",
    ("fetch_red", "api_500"):            "Service error. Please try again later.",
    ("fetch_red", "timeout"):            "Service unavailable. Please try again.",
    ("fetch_red", "malformed_payload"): "The data was unexpected and could not be parsed.",
    ("fetch_red", "missing_field"):      "Red is available, but other fields were missing.",

    # check_17 (successful)
    ("check_17", "successful"):          "Yes, 17 is a prime number.",
    ("check_17", "not_found"):           "Properties not found for that number.",
    ("check_17", "empty"):               "Number information is currently unavailable.",
    ("check_17", "api_400"):             "Invalid request. Please check the number.",
    ("check_17", "api_500"):             "Service error. Please try again later.",
    ("check_17", "timeout"):             "Service unavailable. Please try again.",
    ("check_17", "malformed_payload"):  "The data was unexpected.",

    # describe_pentagon (successful)
    ("describe_pentagon", "successful"): "A pentagon has five sides.",
    ("describe_pentagon", "not_found"):  "Shape not found.",
    ("describe_pentagon", "empty"):      "Shape information is currently unavailable.",
    ("describe_pentagon", "api_400"):    "Invalid request.",
    ("describe_pentagon", "api_500"):    "Service error.",
    ("describe_pentagon", "timeout"):    "Service unavailable.",

    # fetch_red_not_found (real-safe)
    ("fetch_red_not_found", "not_found"): "That color is not found.",
    # fetch_red_empty (real-safe)
    ("fetch_red_empty", "empty"):         "Color information unavailable.",
    # fetch_red_api_400 (mock-only)
    ("fetch_red_api_400", "api_400"):     "Invalid request. Please check your input.",
    # fetch_red_api_500 (mock-only)
    ("fetch_red_api_500", "api_500"):     "Service error. Please try again later.",
    # fetch_red_timeout (mock-only)
    ("fetch_red_timeout", "timeout"):     "Service unavailable. Please try again.",
    # fetch_red_malformed (mock-only)
    ("fetch_red_malformed", "malformed_payload"): "The data was unexpected and could not be parsed.",
}


class MockLLM:
    """Deterministic local LLM. Used only by LocalMockSystem."""

    async def first_call(self, prompt: str, scenario: str) -> dict[str, Any]:
        if scenario not in STUB_RESPONSES:
            raise KeyError(f"Unknown scenario: {scenario!r}")
        return dict(STUB_RESPONSES[scenario])

    async def second_call(
        self,
        scenario: str,
        behavior: str,
        api_response: dict | list | None,
        api_error: str | None,
    ) -> str:
        key = (scenario, behavior)
        if key not in AGENT_MESSAGES:
            # Fall back: any error -> generic message; success -> mention target_api
            if api_error or behavior != "successful":
                return f"Unable to complete request ({behavior})."
            return f"Completed {scenario}."
        return AGENT_MESSAGES[key]