"""AWS Bedrock LLM provider.

Drop-in real LLM provider. Activated by `LLM_PROVIDER=bedrock`.

Requires:

- `pip install aioboto3`
- AWS credentials in env (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)
- A Bedrock model id. Default: anthropic.claude-3-5-sonnet-20241022-v2:0

How it works:

- Uses Bedrock's `converse` API with tool use to force structured output
  matching the LLMResponse schema.
- Returns the same dict shape as the stub provider.
- temperature=0 by default for maximum determinism.
- Two calls per pipeline run: `first_call` for the decision, `second_call`
  for the user-facing agent message after the API response is known.
"""

from __future__ import annotations

import json
import os
from typing import Any


# === Schema definitions (sent to Bedrock as tool-use specs) =========

_DECISION_TOOL = {
    "toolSpec": {
        "name": "llm_decision",
        "description": (
            "Return the agent's decision: which API to call, what action, "
            "and what parameters to pass."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["fetch", "describe", "check", "explain", "list", "compute"],
                    },
                    "target_api": {
                        "type": "string",
                        "enum": ["colors", "numbers", "shapes"],
                    },
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
        "description": (
            "Return the user-facing message the agent will send. "
            "Plain text, no markdown."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                },
                "required": ["message"],
            }
        },
    }
}


# === System prompts =================================================

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


# === Provider implementation ========================================

class BedrockProvider:
    """Async AWS Bedrock LLM provider."""

    def __init__(
        self,
        model_id: str | None = None,
        region: str | None = None,
        temperature: float = 0.0,
    ) -> None:
        self.model_id = model_id or os.environ.get(
            "BEDROCK_MODEL_ID",
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
        )
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.temperature = float(os.environ.get("BEDROCK_TEMPERATURE", str(temperature)))

    def _import_aioboto3(self):
        try:
            import aioboto3  # noqa: F401
            return aioboto3
        except ImportError as exc:
            raise ImportError(
                "BedrockProvider requires `aioboto3`. "
                "Install with: pip install aioboto3"
            ) from exc

    async def _converse(self, *, system: str, user_text: str, tool: dict) -> dict:
        """Single converse call. Returns the parsed tool-use input dict."""
        aioboto3 = self._import_aioboto3()
        session = aioboto3.Session()
        async with session.client("bedrock-runtime", region_name=self.region) as client:
            response = await client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user_text}]}],
                toolConfig={"tools": [tool]},
                inferenceConfig={"temperature": self.temperature},
            )
        return _extract_tool_input(response)

    async def first_call(self, prompt: str, scenario: str) -> dict[str, Any]:
        """Stage 1: user prompt -> LLMDecision."""
        user_text = (
            f"Scenario: {scenario}\n"
            f"User prompt: {prompt}\n\n"
            "Decide which API to call and with what parameters."
        )
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
        """Stage 2: API response -> user-facing message."""
        if api_error:
            response_blob = f"(API error: {api_error})"
        elif api_response is None:
            response_blob = "(API returned no record)"
        else:
            response_blob = json.dumps(api_response, default=str)

        user_text = (
            f"Scenario: {scenario}\n"
            f"API behavior: {behavior}\n"
            f"API response: {response_blob}\n\n"
            "Write the user-facing agent message."
        )
        result = await self._converse(
            system=_AGENT_MESSAGE_SYSTEM_PROMPT,
            user_text=user_text,
            tool=_AGENT_MESSAGE_TOOL,
        )
        return result.get("message", "")


def _extract_tool_input(converse_response: dict) -> dict:
    """Pull the toolUse input dict out of a Bedrock converse response."""
    output = converse_response.get("output", {})
    message = output.get("message", {})
    content = message.get("content", [])
    for block in content:
        if "toolUse" in block:
            tool_use = block["toolUse"]
            if tool_use.get("name") in {"llm_decision", "agent_message"}:
                inp = tool_use.get("input", {})
                if isinstance(inp, str):
                    try:
                        return json.loads(inp)
                    except json.JSONDecodeError:
                        return {}
                return inp
    raise RuntimeError(
        f"Bedrock response had no usable tool use block: {converse_response!r}"
    )