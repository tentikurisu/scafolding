"""API client registry.

Builds the registry from `apis:` config in repeatability.yaml. Each API
entry has:

    apis:
      colors:
        type: stub    # stub | http
        http:
          base_url: http://localhost:8080

When `type=stub`, uses the stub client from `apis.stubs`.
When `type=http`, uses `apis.clients.http.HttpAPIClient` (requires httpx).
Unknown types raise a clear error.

Fallback: when no config file is present, defaults to all-stub.
"""

from __future__ import annotations

from typing import Any, Protocol

from ..apis.stubs import ColorsClient, NumbersClient, ShapesClient
from ..config import get_apis_config


class APIClient(Protocol):
    name: str

    async def call(self, params: dict[str, Any], behavior: str) -> dict[str, Any] | None: ...


# Map of name -> default stub class (used when no config / type=stub)
_DEFAULT_STUB_CLIENTS: dict[str, APIClient] = {
    "colors": ColorsClient(),
    "numbers": NumbersClient(),
    "shapes": ShapesClient(),
}


def _build_http_client(name: str, http_cfg: dict[str, Any]) -> APIClient:
    """Construct an HTTP-backed client. Lazy import httpx."""
    try:
        from ...apis.clients.http import HttpAPIClient  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "HTTP API client requires httpx. Install with: pip install httpx"
        ) from exc
    return HttpAPIClient(name=name, base_url=http_cfg.get("base_url", ""))


def _build_one(name: str, cfg: dict[str, Any]) -> APIClient:
    """Build a single API client from its config block."""
    api_type = cfg.get("type", "stub")
    if api_type == "stub":
        if name in _DEFAULT_STUB_CLIENTS:
            return _DEFAULT_STUB_CLIENTS[name]
        # Generic stub for unknown APIs: uses the name as the lookup key
        from ..apis.stubs import _GenericStubClient
        return _GenericStubClient(name)
    if api_type == "http":
        return _build_http_client(name, cfg.get("http", {}))
    raise ValueError(
        f"Unknown api type {api_type!r} for {name!r}. "
        f"Supported: stub, http"
    )


class APIClientRegistry:
    def __init__(self, clients: dict[str, APIClient]) -> None:
        self._clients = dict(clients)

    def get(self, name: str) -> APIClient:
        if name not in self._clients:
            raise KeyError(f"No API client registered for {name!r}")
        return self._clients[name]

    def names(self) -> list[str]:
        return list(self._clients.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._clients


def build_default_registry() -> APIClientRegistry:
    """Build the registry from the current config. Falls back to all stubs."""
    apis_cfg = get_apis_config()
    if not apis_cfg:
        return APIClientRegistry(dict(_DEFAULT_STUB_CLIENTS))
    clients: dict[str, APIClient] = {}
    for name, cfg in apis_cfg.items():
        if not isinstance(cfg, dict):
            continue
        clients[name] = _build_one(name, cfg)
    # If config was empty/filtered, fall back to defaults
    if not clients:
        return APIClientRegistry(dict(_DEFAULT_STUB_CLIENTS))
    return APIClientRegistry(clients)


def reload_from_config() -> APIClientRegistry:
    """Rebuild the registry from current config (after reload_config())."""
    return build_default_registry()