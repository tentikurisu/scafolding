"""HTTP API adapter for independent API contract tests.

Reusable, env-driven, never holds committed credentials. Suitable for
testing API endpoints directly (not via the Lambda). The fictional example
shows the shape; replace endpoint/params/headers/mapping with your real API.
"""

from __future__ import annotations

from typing import Any, Optional, Type

import httpx
from pydantic import BaseModel


# === Specific exception types (preserve status codes from real errors) ===

class APIError(Exception):
    """Base for HTTP API adapter errors. Preserves status + details."""
    def __init__(self, status: int, url: str, message: str, body: Optional[str] = None) -> None:
        super().__init__(f"{status} {url}: {message}")
        self.status = status
        self.url = url
        self.message = message
        self.body = body  # raw response body for debugging


class APIClientError(APIError):     pass  # 4xx
class APIAuthError(APIError):       pass  # 401/403
class APINotFoundError(APIError):   pass  # 404 (raised when caller wants exception instead of None)
class APIServerError(APIError):     pass  # 5xx


_ERROR_FOR_STATUS = {
    400: APIClientError,
    401: APIAuthError,
    403: APIAuthError,
    404: APINotFoundError,
}


def _exception_for_status(status: int, url: str, message: str, body: Optional[str]) -> APIError:
    if status in _ERROR_FOR_STATUS:
        return _ERROR_FOR_STATUS[status](status, url, message, body)
    if status >= 500:
        return APIServerError(status, url, message, body)
    return APIError(status, url, message, body)


# === Adapter =========================================================

class ApiAdapter:
    """Reusable HTTP adapter for one API base URL.

    Configuration via constructor args (which the conftest populates from
    env vars). No credentials committed to source. The single
    `request_and_normalize` method handles auth, error mapping, and
    response validation — one place to change when the contract evolves.
    """

    def __init__(
        self,
        base_url: str,
        *,
        default_headers: Optional[dict[str, str]] = None,
        schema: Optional[Type[BaseModel]] = None,
        timeout_s: float = 5.0,
    ) -> None:
        if not base_url:
            raise ValueError("ApiAdapter requires a non-empty base_url")
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}
        self.schema = schema
        self.timeout_s = timeout_s

    def _headers(self, extra: Optional[dict[str, str]]) -> dict[str, str]:
        merged = dict(self.default_headers)
        if extra:
            merged.update(extra)
        return merged

    async def request_and_normalize(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
        headers: Optional[dict[str, str]] = None,
        not_found_returns_none: bool = True,
    ) -> dict | list | None:
        """Single entry point: do the request, handle errors, validate, return.

        - 404 -> None (if not_found_returns_none) or APINotFoundError
        - Other 4xx -> APIClientError / APIAuthError
        - 5xx -> APIServerError
        - Success -> validates against self.schema if set, else returns JSON
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(
            base_url=self.base_url, timeout=self.timeout_s,
            headers=self._headers(headers),
        ) as client:
            try:
                resp = await client.request(method, url, params=params, json=json_body)
            except httpx.TimeoutException as exc:
                raise APIServerError(0, url, f"timeout: {exc}", body=None) from exc

        body_text = resp.text if resp.content else None

        if resp.status_code == 404 and not_found_returns_none:
            return None
        if resp.status_code >= 400:
            raise _exception_for_status(resp.status_code, url, resp.reason_phrase, body_text)
        if not resp.content:
            return None

        data = resp.json()
        if self.schema is not None:
            return self.schema.model_validate(data).model_dump(exclude_none=False)
        return data

    # === Fictional example ===========================================

    async def fetch_color(self, name: str) -> dict | None:
        """Fictional example. Replace with your real endpoint.

        Endpoint:   GET /colors/{name}
        Auth:       Bearer token via default_headers
        Schema:     ColorsResponse
        404 ->      None
        """
        from .api_schemas import ColorsResponse  # local to this module
        return await self.request_and_normalize(
            "GET", f"/colors/{name}", schema=ColorsResponse,
        )