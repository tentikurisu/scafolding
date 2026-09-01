"""LLM client. Provider-agnostic; dispatches by env or constructor arg.

Usage:

    client = LLMClient()                            # uses LLM_PROVIDER env (default: stub)
    client = LLMClient(provider="bedrock")          # explicit override
    client = LLMClient(provider="stub")             # force stubs

The pipeline code never needs to know which provider is in use.
"""

from __future__ import annotations

import os
from typing import Any

from ..llm.providers import ProviderProtocol, get_provider


class LLMClient:
    """Two-stage LLM client: decision + agent message."""

    def __init__(self, provider: str | None = None) -> None:
        provider_name = provider or os.environ.get("LLM_PROVIDER", "stub")
        self.provider_name = provider_name
        self._provider: ProviderProtocol = get_provider(provider_name)

    async def ask(self, prompt: str, scenario: str) -> dict[str, Any]:
        """First LLM call. Returns decision dict."""
        return await self._provider.first_call(prompt, scenario)

    async def generate_agent_message(
        self,
        scenario: str,
        behavior: str,
        api_response: dict | None,
        api_error: str | None,
    ) -> str:
        """Second LLM call. Returns the user-facing agent message."""
        return await self._provider.second_call(
            scenario=scenario,
            behavior=behavior,
            api_response=api_response,
            api_error=api_error,
        )

    @property
    def provider(self) -> ProviderProtocol:
        """Underlying provider object. Useful for tests that want to inspect."""
        return self._provider