"""Execution lambda + mock API clients.

The lambda orchestrates: prompt -> LLM decision -> API call -> agent message.

The API clients in this file are MOCKS — minimal placeholders used by tests
when you don't have (or don't want to use) real APIs. Replace them with
your real DB-backed / HTTP clients when ready. See SWAP_GUIDE.md and
real_examples.py.

9 API behaviors (placeholders to swap with real error injection):
  - successful, empty, not_found, missing_field, malformed_payload
  - api_400, api_401_403, api_500, timeout
"""

from __future__ import annotations

from typing import Any, Protocol


# === API contract ====================================================
# BOTH mocks and real clients implement this.

class APIClient(Protocol):
    name: str

    async def call(self, params: dict, behavior: str) -> dict | None: ...


class ExecutionLambda:
    """Three stages: LLM decision -> API call -> LLM agent message."""

    def __init__(self, llm: Any, api_clients: dict[str, APIClient]) -> None:
        self.llm = llm
        self.apis = api_clients

    async def handle(
        self,
        prompt: str,
        scenario: str,
        *,
        behavior: str = "successful",
    ) -> dict[str, Any]:
        # Stage 1: LLM decides what API to call
        decision = await self.llm.first_call(prompt, scenario)
        target_api = decision.get("target_api", "")
        params = decision.get("params", {}) or {}

        # Stage 2: API call (behavior injected by tests)
        api_response: dict | None = None
        api_error: str | None = None
        if target_api not in self.apis:
            api_error = f"UnknownTargetAPI:{target_api}"
        else:
            try:
                api_response = await self.apis[target_api].call(params, behavior)
            except Exception as exc:
                api_error = type(exc).__name__

        # Stage 3: LLM drafts user-facing message
        agent_message = await self.llm.second_call(
            scenario=scenario,
            behavior=behavior,
            api_response=api_response,
            api_error=api_error,
        )

        return {
            "scenario": scenario,
            "behavior": behavior,
            "llm_decision": decision,
            "target_api": target_api,
            "api_response": api_response,
            "api_error": api_error,
            "agent_message": agent_message,
        }


# === Mock API clients ================================================
# These are MOCKS. Used by tests when no real API is wired in. Replace
# MockColorsAPI / MockNumbersAPI / MockShapesAPI with your real clients.

class _MockAPIBase:
    name: str = ""
    _payload: dict = {}

    async def call(self, params: dict, behavior: str) -> dict | None:
        if behavior in ("api_400", "api_401_403", "api_500", "timeout"):
            raise RuntimeError(f"Simulated {behavior}")
        if behavior == "not_found":
            return None
        if behavior == "empty":
            return {}
        if behavior == "missing_field":
            return {k: self._payload[k] for k in list(self._payload.keys())[:2]}
        if behavior == "malformed_payload":
            return {"raw": "not-a-valid-record"}
        return dict(self._payload)


class MockColorsAPI(_MockAPIBase):
    name = "colors"
    _payload = {"name": "red", "hex": "#FF0000", "rgb": [255, 0, 0]}


class MockNumbersAPI(_MockAPIBase):
    name = "numbers"
    _payload = {"n": 17, "is_prime": True, "parity": "odd"}


class MockShapesAPI(_MockAPIBase):
    name = "shapes"
    _payload = {"name": "pentagon", "sides": 5}


def default_mock_apis() -> dict[str, APIClient]:
    """Default registry of the 3 mock APIs. Replace with your real clients."""
    return {
        "colors": MockColorsAPI(),
        "numbers": MockNumbersAPI(),
        "shapes": MockShapesAPI(),
    }