"""HTTP-backed API clients.

Real `httpx.AsyncClient`-based clients. Used when an API in
repeatability.yaml has `type: http`.

Mapping conventions (configurable per API in the future):

- colors  -> GET {base_url}/colors/{name}
- numbers -> GET {base_url}/numbers/{n}/properties
- shapes  -> GET {base_url}/shapes/{name}

Errors:

- 400 -> BadRequestError
- 401/403 -> AuthError
- 404 -> returns None (not_found)
- 500 -> ServerError
- timeout -> TimeoutError_

For behaviors like `empty`, `missing_field`, `malformed_payload`, this client
returns whatever the server returns; it does not synthesize responses. Use
the stubs as the fault-injection layer for those behaviors.
"""

from __future__ import annotations

from typing import Any

import httpx

from ...stubs import (
    AuthError,
    BadRequestError,
    ServerError,
    TimeoutError_,
)


def _map_status_error(status: int) -> type[Exception] | None:
    if status == 400:
        return BadRequestError
    if status in (401, 403):
        return AuthError
    if status >= 500:
        return ServerError
    return None


class HttpAPIClient:
    """Single generic HTTP client. Plugged in by name from api_registry."""

    def __init__(self, name: str, base_url: str) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=5.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _path(self, params: dict[str, Any]) -> str:
        if self.name == "colors":
            return f"/colors/{params.get('name', 'unknown')}"
        if self.name == "numbers":
            return f"/numbers/{params.get('n', 0)}/properties"
        if self.name == "shapes":
            return f"/shapes/{params.get('name', 'unknown')}"
        # Generic fallback: POST to /{name} with params as body
        return f"/{self.name}"

    async def call(self, params: dict[str, Any], behavior: str) -> dict[str, Any] | None:
        client = await self._http()
        path = self._path(params)
        try:
            resp = await client.get(path, params={"behavior": behavior})
        except httpx.TimeoutException as exc:
            raise TimeoutError_(f"request to {path} timed out") from exc

        if resp.status_code == 404:
            return None
        err_cls = _map_status_error(resp.status_code)
        if err_cls is not None:
            raise err_cls(f"{resp.status_code} from {path}")

        resp.raise_for_status()
        if not resp.content:
            return None
        return resp.json()