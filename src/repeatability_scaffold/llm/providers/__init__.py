"""LLM provider registry.

A "provider" is a module that exposes two async functions matching the
`ProviderProtocol`:

    async def first_call(prompt: str, scenario: str) -> dict[str, Any]
    async def second_call(
        scenario: str, behavior: str,
        api_response: dict | None, api_error: str | None,
    ) -> str

Built-in providers:

- `stub`     - deterministic, no network. Default.
- `bedrock`  - AWS Bedrock via aioboto3. Activated by `LLM_PROVIDER=bedrock`.

Add a new provider by:

1. Creating `src/repeatability_scaffold/llm/providers/<name>.py`
2. Implementing the two functions
3. Registering it in `_REGISTRY` below
4. Selecting it with `LLM_PROVIDER=<name>` or `LLMClient(provider=<name>)`

The pipeline and tests do not change.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Protocol


class ProviderProtocol(Protocol):
    """Interface every provider must satisfy."""

    async def first_call(self, prompt: str, scenario: str) -> dict[str, Any]: ...
    async def second_call(
        self,
        scenario: str,
        behavior: str,
        api_response: dict[str, Any] | None,
        api_error: str | None,
    ) -> str: ...


# Registry: name -> factory returning a ProviderProtocol implementation.
_REGISTRY: dict[str, Callable[[], ProviderProtocol]] = {}


def register_provider(name: str, factory: Callable[[], ProviderProtocol]) -> None:
    """Register a new provider. Called by provider modules on import."""
    _REGISTRY[name] = factory


def get_provider(name: str) -> ProviderProtocol:
    if name not in _REGISTRY:
        raise KeyError(
            f"Unknown LLM provider {name!r}. "
            f"Registered: {sorted(_REGISTRY)}. "
            f"Set LLM_PROVIDER in env or pass provider= to LLMClient()."
        )
    return _REGISTRY[name]()


def available_providers() -> list[str]:
    return sorted(_REGISTRY)


# === Built-in registrations ==========================================

def _build_stub() -> ProviderProtocol:
    from ..stub_provider import StubProvider
    return StubProvider()


register_provider("stub", _build_stub)


def _build_bedrock() -> ProviderProtocol:
    # Lazy import: aioboto3 may not be installed in every env.
    from .bedrock_provider import BedrockProvider
    return BedrockProvider()


register_provider("bedrock", _build_bedrock)