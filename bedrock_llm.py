"""Bedrock LLM — real AWS Bedrock implementation.

Drop-in replacement for MockLLM. Same interface (first_call, second_call).

Install:  pip install aioboto3
AWS auth: any method supported by boto3 (env vars, ~/.aws/credentials, IAM role, etc.)

Configuration (env vars):
    AWS_REGION              (default: us-east-1)
    BEDROCK_MODEL_ID        (default: anthropic.claude-3-5-sonnet-20241022-v2:0)
    BEDROCK_TEMPERATURE     (default: 0.0 — for determinism)

Usage in conftest.py:

    from bedrock_llm import BedrockLLM
    llm_factory = BedrockLLM         # uses env vars for config
    # or with explicit config:
    llm_factory = lambda: BedrockLLM(model_id="...", region="...")

The scaffold tests run unchanged — only the factory line in conftest.py
changes from MockLLM to BedrockLLM.
"""

from __future__ import annotations

import json
import os
from typing import Any


# === Schema definitions (sent to Bedrock as tool-use specs) ==========

_DECISION_TOOL = {
    "toolSpec": {
        "name": "llm_decision",
        "description": "Return the agent's decision: which API to call and what params.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "target_api": {"type": "string"},
                    "params": {"type": "object"},
                    "reasoning": {"type": "string"},
                },
                "required": ["action", "target_api", "params", "reasoning"],
            }
        },
    }
}

_AGENT_MESSAGE_TOOL = {
    "toolSpec": {
        "name": "agent_message",
        "description": "Return the user-facing message the agent will send.",
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            }
        },
    }
}

_DECISION_SYSTEM_PROMPT = (
    "You are an agent router. Given a user prompt, decide which API to call "
    "and what parameters to use. Always respond by calling the "
    "llm_decision tool exactly once. Do not include any other text."
)

_AGENT_MESSAGE_SYSTEM_PROMPT = (
    "You are a careful agent. You have just received an API response. "
    "Write a short, honest user-facing message. "
    "Rules: "
    "(1) If the API returned data, use it - do not invent. "
    "(2) If the API returned empty or no record, say so. "
    "(3) If a field is missing, acknowledge it. "
    "(4) If the API errored, explain the failure in plain language. "
    "(5) Never invent values, names, codes, or facts not present in the data. "
    "Always respond by calling the agent_message tool exactly once."
)


# === BedrockLLM ======================================================

class BedrockLLM:
    """Real AWS Bedrock LLM. Drop-in replacement for MockLLM.

    Requires:
        - aioboto3 (pip install aioboto3)
        - AWS credentials (any boto3-supported method)

    Configure via env vars or constructor args.
    """

    DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    DEFAULT_REGION = "us-east-1"
    DEFAULT_TEMPERATURE = 0.0

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
        temperature: float | None = None,
    ) -> None:
        self.model_id = model_id or os.environ.get("BEDROCK_MODEL_ID", self.DEFAULT_MODEL_ID)
        self.region = region or os.environ.get("AWS_REGION", self.DEFAULT_REGION)
        self.temperature = float(
            os.environ.get("BEDROCK_TEMPERATURE", str(temperature if temperature is not None else self.DEFAULT_TEMPERATURE))
        )

    def _session(self):
        """Lazy import so aioboto3 isn't required for the mock-only path."""
        try:
            import aioboto3
        except ImportError as exc:
            raise ImportError(
                "BedrockLLM requires aioboto3. Install with: pip install aioboto3"
            ) from exc
        return aioboto3.Session()

    async def _converse(self, *, system: str, user_text: str, tool: dict) -> dict:
        """Single converse call. Returns the parsed tool-use input dict."""
        session = self._session()
        async with session.client("bedrock-runtime", region_name=self.region) as client:
            resp = await client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user_text}]}],
                toolConfig={"tools": [tool]},
                inferenceConfig={"temperature": self.temperature},
            )
        return _extract_tool_input(resp, tool_name=tool["toolSpec"]["name"])

    async def first_call(self, prompt: str, scenario: str) -> dict[str, Any]:
        """Stage 1: user prompt -> LLM decision (what API to call)."""
        user_text = f"Scenario: {scenario}\nUser prompt: {prompt}"
        return await self._converse(
            system=_DECISION_SYSTEM_PROMPT,
            user_text=user_text,
            tool=_DECISION_TOOL,
        )

    async def second_call(
        self,
        scenario: str,
        behavior: str,
        api_response: dict | None,
        api_error: str | None,
    ) -> str:
        """Stage 2: API response -> user-facing agent message."""
        if api_error:
            response_blob = f"(API error: {api_error})"
        elif api_response is None:
            response_blob = "(API returned no record)"
        else:
            response_blob = json.dumps(api_response, default=str)

        user_text = (
            f"Scenario: {scenario}\n"
            f"API behavior: {behavior}\n"
            f"API response: {response_blob}"
        )
        result = await self._converse(
            system=_AGENT_MESSAGE_SYSTEM_PROMPT,
            user_text=user_text,
            tool=_AGENT_MESSAGE_TOOL,
        )
        return result.get("message", "")


# === Tool-use extraction =============================================

def _extract_tool_input(converse_response: dict, *, tool_name: str) -> dict:
    """Pull the toolUse input dict out of a Bedrock converse response."""
    output = converse_response.get("output", {})
    message = output.get("message", {})
    content = message.get("content", [])
    for block in content:
        if "toolUse" in block:
            tool_use = block["toolUse"]
            if tool_use.get("name") == tool_name:
                inp = tool_use.get("input", {})
                if isinstance(inp, str):
                    try:
                        return json.loads(inp)
                    except json.JSONDecodeError:
                        return {}
                return inp
    raise RuntimeError(
        f"Bedrock response had no {tool_name!r} tool use block: {converse_response!r}"
    )