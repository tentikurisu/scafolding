"""Stubbed API clients.

Each client can simulate 9 placeholder behaviors:

- `successful`            - full valid response
- `empty`                 - `{}`
- `not_found`             - `None`
- `missing_field`         - partial response (subset of fields)
- `malformed_payload`     - response with wrong types / shapes
- `api_400`               - raises BadRequestError
- `api_401_403`           - raises AuthError
- `api_500`               - raises ServerError
- `timeout`               - raises TimeoutError_

Swap-in point: replace the body of each `call` with `httpx.AsyncClient` calls.
The interface does not change.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol


# === Error types =====================================================

class BadRequestError(Exception):
    """Simulated 400 response."""


class NotFoundError(Exception):
    """Simulated 404 response (used by some behaviors)."""


class AuthError(Exception):
    """Simulated 401/403 response."""


class ServerError(Exception):
    """Simulated 500 response."""


class TimeoutError_(Exception):
    """Simulated timeout. Underscore suffix to avoid shadowing builtin."""

    def __init__(self, message: str = "request timed out") -> None:
        super().__init__(message)
        self.message = message


ERROR_BEHAVIOR_TO_EXCEPTION: dict[str, type[Exception]] = {
    "api_400": BadRequestError,
    "api_401_403": AuthError,
    "api_500": ServerError,
    "timeout": TimeoutError_,
}


def make_error(behavior: str, message: str | None = None) -> Exception:
    """Construct the matching exception for an error-shaped behavior."""
    cls = ERROR_BEHAVIOR_TO_EXCEPTION[behavior]
    if cls is TimeoutError_:
        return cls(message or "request timed out")
    return cls(message or behavior)


# === Stubbed payloads ===============================================

_COLORS_SUCCESSFUL: dict[str, Any] = {
    "name": "red",
    "hex": "#FF0000",
    "rgb": [255, 0, 0],
    "family": "red",
    "complementary": "#00FFFF",
}

_COLORS_XYZ_SUCCESSFUL: dict[str, Any] = {
    "name": "xyz",
    "hex": "#ABCDEF",
    "rgb": [171, 205, 239],
    "family": "blue",
    "complementary": "#FEDCBA",
}

_NUMBERS_PRIME_17_SUCCESSFUL: dict[str, Any] = {
    "n": 17,
    "is_prime": True,
    "is_square": False,
    "parity": "odd",
    "factors": [1, 17],
}

_NUMBERS_NEGATIVE_SUCCESSFUL: dict[str, Any] = {
    "n": -7,
    "is_prime": False,
    "is_square": False,
    "parity": "odd",
    "factors": [-1, 1, 7],
}

_SHAPES_PENTAGON_SUCCESSFUL: dict[str, Any] = {
    "name": "pentagon",
    "sides": 5,
    "area_formula": "(1/4) * sqrt(5*(5+2*sqrt(5))) * a^2",
    "regular": True,
}

_SHAPES_UNKNOWN_SUCCESSFUL: dict[str, Any] = {
    "name": "hexaflexagon",
    "sides": 6,
    "area_formula": "complex",
    "regular": True,
}


def _colors_payload(params: dict, behavior: str) -> dict | None:
    if behavior == "successful":
        if params.get("name") == "xyz":
            return _COLORS_XYZ_SUCCESSFUL
        return _COLORS_SUCCESSFUL
    if behavior == "empty":
        return {}
    if behavior == "not_found":
        return None
    if behavior == "missing_field":
        return {"name": params.get("name", "red"), "hex": "#FF0000"}
    if behavior == "malformed_payload":
        return {"name": params.get("name", "red"), "hex": 12345, "rgb": "not-a-list"}
    raise ValueError(f"colors stub: behavior {behavior!r} should have raised")


def _numbers_payload(params: dict, behavior: str) -> dict | None:
    if behavior == "successful":
        n = params.get("n", 17)
        if not isinstance(n, int):
            return _NUMBERS_PRIME_17_SUCCESSFUL
        # Deterministic stub: 17 -> known prime result; -7 -> known negative result;
        # any other n -> generic computed result honoring parity / primality for small n.
        if n == 17:
            return _NUMBERS_PRIME_17_SUCCESSFUL
        if n < 0:
            return {
                "n": n,
                "is_prime": False,
                "is_square": False,
                "parity": "odd" if abs(n) % 2 else "even",
                "factors": [-1, 1, abs(n)] if n != 0 else [1],
            }
        # General path: compute parity, basic primality for small positive ints.
        is_prime = n > 1 and all(n % i != 0 for i in range(2, min(n, int(n**0.5) + 1)))
        is_square = int(n**0.5) ** 2 == n
        factors = [i for i in range(1, n + 1) if n % i == 0] if n > 0 else [0]
        return {
            "n": n,
            "is_prime": is_prime,
            "is_square": is_square,
            "parity": "even" if n % 2 == 0 else "odd",
            "factors": factors,
        }
    if behavior == "empty":
        return {}
    if behavior == "not_found":
        return None
    if behavior == "missing_field":
        return {"n": params.get("n", 17), "is_prime": True}
    if behavior == "malformed_payload":
        return {"n": "seventeen", "is_prime": "yes"}
    raise ValueError(f"numbers stub: behavior {behavior!r} should have raised")


def _shapes_payload(params: dict, behavior: str) -> dict | None:
    if behavior == "successful":
        if params.get("name") == "hexaflexagon":
            return _SHAPES_UNKNOWN_SUCCESSFUL
        return _SHAPES_PENTAGON_SUCCESSFUL
    if behavior == "empty":
        return {}
    if behavior == "not_found":
        return None
    if behavior == "missing_field":
        return {"name": params.get("name", "pentagon"), "sides": 5}
    if behavior == "malformed_payload":
        return {"name": params.get("name", "pentagon"), "sides": "five"}
    raise ValueError(f"shapes stub: behavior {behavior!r} should have raised")


_PAYLOAD_BUILDERS = {
    "colors": _colors_payload,
    "numbers": _numbers_payload,
    "shapes": _shapes_payload,
}


# === Client classes ================================================

class APIClient(Protocol):
    async def call(self, params: dict, behavior: str) -> dict | None: ...
    name: str


class _BaseStubClient:
    name: str = ""

    def __init__(self) -> None:
        pass

    async def call(self, params: dict, behavior: str) -> dict | None:
        if behavior in ERROR_BEHAVIOR_TO_EXCEPTION:
            await asyncio.sleep(0)
            raise make_error(behavior)
        builder = _PAYLOAD_BUILDERS[self.name]
        await asyncio.sleep(0)
        return builder(params, behavior)


class ColorsClient(_BaseStubClient):
    name = "colors"


class NumbersClient(_BaseStubClient):
    name = "numbers"


class ShapesClient(_BaseStubClient):
    name = "shapes"


class _GenericStubClient(_BaseStubClient):
    """Generic stub used for APIs not in the default set.

    Has no scenario-aware payload logic; returns empty dicts or raises the
    matching error for failure behaviors. Useful when the user adds a new
    API to config without writing a custom stub class.
    """

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    async def call(self, params: dict, behavior: str) -> dict | None:
        if behavior in ERROR_BEHAVIOR_TO_EXCEPTION:
            await asyncio.sleep(0)
            raise make_error(behavior)
        if behavior == "not_found":
            return None
        if behavior == "empty":
            return {}
        if behavior == "missing_field":
            return {}
        if behavior == "malformed_payload":
            return {"_malformed": True}
        # successful and any other: return empty dict
        return {"name": self.name}