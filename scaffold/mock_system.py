"""LocalMockSystem — runs the mocked LLM/API orchestration locally.

This is one of two SystemUnderTest implementations. Used by default
when TEST_TARGET=mock (or unset). Deterministic, fast, no AWS.
"""

from __future__ import annotations

from typing import Any

from .mock_apis import FaultInjector, default_mock_apis
from .mock_llm import MockLLM
from .models import ExecutionResult
from .validators import category_for_error


class LocalMockSystem:
    """Runs the LLM -> API -> LLM pipeline locally with mocks.

    The full call graph:
        invoke(prompt, scenario, behavior)
            -> llm.first_call()        # what API to hit
            -> fault_injected_api.call()  # simulate the behavior
            -> llm.second_call()       # write user-facing message
            -> ExecutionResult
    """

    def __init__(self, llm: Any = None, api_registry: dict | None = None) -> None:
        self.llm = llm or MockLLM()
        self.api_registry = api_registry or default_mock_apis()
        # Wrap each registered API in a FaultInjector. The local mock
        # system is the only place that knows about behavior injection.
        self._fault_clients = {
            name: FaultInjector(client) for name, client in self.api_registry.items()
        }

    async def invoke(
        self,
        prompt: str,
        scenario: str | None = None,
        behavior: str = "successful",
    ) -> ExecutionResult:
        """Execute one full pipeline run. Returns a normalized ExecutionResult."""
        scenario = scenario or "default"

        # Stage 1: LLM decides what API to call
        decision = await self.llm.first_call(prompt, scenario)
        target_api = decision.get("target_api", "")
        params = decision.get("params", {}) or {}

        # Stage 2: API call with behavior injection
        api_response: dict | list | None = None
        api_error: str | None = None
        api_error_category: str | None = None
        if not target_api:
            api_error = "UnknownTargetAPI"
            api_error_category = "client_error"
        elif target_api not in self._fault_clients:
            api_error = f"UnknownTargetAPI:{target_api}"
            api_error_category = "client_error"
        else:
            try:
                api_response = await self._fault_clients[target_api].call(
                    params, behavior=behavior,
                )
            except Exception as exc:
                api_error = type(exc).__name__
                api_error_category = category_for_error(exc)

        # Stage 3: LLM drafts the user-facing message
        agent_message = await self.llm.second_call(
            scenario=scenario, behavior=behavior,
            api_response=api_response, api_error=api_error,
        )

        return ExecutionResult(
            response_text=agent_message,
            target_api=target_api if not api_error else None,
            tool_parameters=params,
            api_response=api_response,
            api_error=api_error,
            api_error_category=api_error_category,
            raw_response={"decision": decision, "behavior": behavior},
        )