"""Mock API clients + FaultInjector wrapper.

Production-style APIClient protocol:
    async def call(self, params: dict) -> dict | list | None: ...

Mock clients implement that interface and return normal data (no behavior arg).
FaultInjector wraps any APIClient and injects fake failures based on a
configured behavior. This separation means production code never sees a
behavior argument.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Protocol


# === Production-style interface =====================================
# No behavior argument. Production clients implement this as-is.

class APIClient(Protocol):
    name: str

    async def call(self, params: dict) -> dict | list | None:
        """Return response data, None for not_found, raise for errors."""
        ...


# === Mock clients (look like production) =============================

class MockColorsClient:
    name = "colors"
    _data = {"name": "red", "hex": "#FF0000", "rgb": [255, 0, 0]}

    async def call(self, params: dict) -> dict | list | None:
        return dict(self._data)


class MockNumbersClient:
    name = "numbers"
    _data = {"n": 17, "is_prime": True, "parity": "odd"}

    async def call(self, params: dict) -> dict | list | None:
        return dict(self._data)


class MockShapesClient:
    name = "shapes"
    _data = {"name": "pentagon", "sides": 5}

    async def call(self, params: dict) -> dict | list | None:
        return dict(self._data)


def default_mock_apis() -> dict[str, APIClient]:
    """Return a registry of mock API clients (production-style interface)."""
    return {
        "colors": MockColorsClient(),
        "numbers": MockNumbersClient(),
        "shapes": MockShapesClient(),
    }


# === Fault injection (local test-only) ==============================
# Wraps a real-style APIClient and simulates failure modes by raising or
# returning special values. This is the ONLY layer that knows about
# "behaviors". Production code never sees this.

class SimulatedError(Exception):
    """Base for all simulated errors. Carries the behavior label."""
    def __init__(self, behavior: str, message: str = "") -> None:
        super().__init__(message or behavior)
        self.behavior = behavior


class SimulatedBadRequest(SimulatedError):     pass  # 400
class SimulatedAuthError(SimulatedError):       pass  # 401/403
class SimulatedServerError(SimulatedError):     pass  # 500
class SimulatedTimeout(SimulatedError):         pass  # timeout


_BEHAVIOR_TO_EXCEPTION = {
    "api_400":     SimulatedBadRequest,
    "api_401_403": SimulatedAuthError,
    "api_500":     SimulatedServerError,
    "timeout":     SimulatedTimeout,
}


class FaultInjector:
    """Wraps an APIClient to inject fake failure modes by behavior.

    Usage in LocalMockSystem:
        client = FaultInjector(MockColorsClient())
        result = await client.call({"name": "red"}, behavior="api_500")  # raises
    """

    def __init__(self, client: APIClient) -> None:
        self._client = client

    async def call(self, params: dict, *, behavior: str = "successful") -> dict | list | None:
        # Fault injection
        if behavior == "not_found":
            return None
        if behavior == "empty":
            return {}
        if behavior == "missing_field":
            full = await self._client.call(params)
            if isinstance(full, dict):
                return {k: full[k] for k in list(full.keys())[:2]}
            return {}
        if behavior == "malformed_payload":
            return {"_malformed": True, "raw": "not-a-valid-record"}
        exc_cls = _BEHAVIOR_TO_EXCEPTION.get(behavior)
        if exc_cls is not None:
            await asyncio.sleep(0)
            raise exc_cls(behavior)

        # Normal pass-through to the underlying client
        return await self._client.call(params)