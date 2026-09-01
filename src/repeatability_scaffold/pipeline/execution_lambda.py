"""Execution lambda.

The lambda takes a user prompt + scenario, calls the LLM to decide what API to
hit, calls the API (with a configurable placeholder behavior), then asks the
LLM to draft the user-facing agent message.

The `behavior` argument lets tests inject failure modes into the API stub
without changing the lambda's logic.
"""

from __future__ import annotations

from typing import Any

from ..apis.evaluator import assert_schema_valid
from ..apis.schemas import API_SCHEMAS
from .api_registry import APIClientRegistry
from .llm_client import LLMClient


class ExecutionLambda:
    def __init__(
        self,
        llm_client: LLMClient,
        api_registry: APIClientRegistry,
    ) -> None:
        self.llm = llm_client
        self.registry = api_registry

    async def handle(
        self,
        prompt: str,
        scenario: str,
        *,
        behavior: str = "successful",
    ) -> dict[str, Any]:
        # Stage 1: LLM decides what API to call.
        decision = await self.llm.ask(prompt, scenario)

        # Stage 2: Execute the API call (with placeholder behavior).
        target_api: str = decision.get("target_api", "")
        params: dict = decision.get("params", {}) or {}

        api_response: dict | None = None
        api_error: str | None = None
        if target_api not in self.registry:
            api_error = f"UnknownTargetAPI:{target_api}"
        else:
            client = self.registry.get(target_api)
            try:
                api_response = await client.call(params, behavior)
            except Exception as exc:
                api_error = type(exc).__name__

        # Stage 3: Validate successful-shaped responses against the schema.
        # Errors / None / {} are tolerated and passed through to the LLM.
        validated_response: dict | None = api_response
        if api_response is not None and api_error is None:
            schema = API_SCHEMAS[target_api]
            try:
                validated = schema.model_validate(api_response)
                validated_response = validated.model_dump(exclude_none=False)
            except Exception:
                validated_response = api_response  # malformed_payload path

        # Stage 4: LLM drafts the user-facing message.
        agent_message = await self.llm.generate_agent_message(
            scenario=scenario,
            behavior=behavior,
            api_response=validated_response,
            api_error=api_error,
        )

        return {
            "scenario": scenario,
            "behavior": behavior,
            "llm_decision": decision,
            "target_api": target_api,
            "api_response": validated_response,
            "api_error": api_error,
            "agent_message": agent_message,
        }