"""Assess primitives for LLM responses and API results.

These are the preserved useful bits from the original scaffold:
  - contains_all()         — substring match across required tokens
  - jaccard()              — similarity across N responses
  - fields_match()         — per-field equality (forgiving of extras)
  - validate_pydantic()    — schema validation helper

Tests use these to assert semantic properties instead of exact strings.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from pydantic import BaseModel


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def contains_all(text: str, tokens: Iterable[str]) -> bool:
    """True iff every token appears in `text` (case-insensitive substring)."""
    if not text:
        return False
    lower = text.lower()
    return all(t.lower() in lower for t in tokens)


def contains_none(text: str, forbidden: Iterable[str]) -> bool:
    """True iff no forbidden token appears in `text` (case-insensitive)."""
    if not text:
        return True
    lower = text.lower()
    return all(t.lower() not in lower for t in forbidden)


def jaccard(texts: Iterable[str]) -> float:
    """Token-set Jaccard similarity across N texts. 1.0 = identical."""
    sets = [{t.lower() for t in _TOKEN_RE.findall(s)} for s in texts]
    if not sets:
        return 1.0
    if len(sets) == 1:
        return 1.0
    union: set[str] = set().union(*sets)
    if not union:
        return 1.0
    inter = sets[0].intersection(*sets[1:])
    return len(inter) / len(union)


def fields_match(actual: dict, expected: dict) -> bool:
    """True iff every field in `expected` exists in `actual` with the same value.
    Extra fields in `actual` are ignored (forgiving)."""
    return all(actual.get(k) == v for k, v in expected.items())


def fields_match_report(actual: dict, expected: dict) -> dict[str, bool]:
    """Per-field equality report."""
    return {k: actual.get(k) == v for k, v in expected.items()}


def validate_pydantic(raw: Any, schema: type[BaseModel]) -> BaseModel:
    """Parse `raw` into the given Pydantic schema. Raises on invalid input."""
    return schema.model_validate(raw)


def category_for_error(exc: BaseException | None) -> str | None:
    """Map an exception to a coarse error category, or None.

    Categories: success, client_error, auth_error, server_error, timeout,
                not_found, empty, unknown_error.
    """
    if exc is None:
        return None
    # Recognise scaffold's own Simulated* exceptions first (precise).
    from .mock_apis import (
        SimulatedTimeout, SimulatedBadRequest,
        SimulatedAuthError, SimulatedServerError,
    )
    if isinstance(exc, SimulatedTimeout):
        return "timeout"
    if isinstance(exc, SimulatedAuthError):
        return "auth_error"
    if isinstance(exc, SimulatedBadRequest):
        return "client_error"
    if isinstance(exc, SimulatedServerError):
        return "server_error"

    # Real adapter / HTTP exceptions.
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "auth" in name or "403" in name or "401" in name:
        return "auth_error"
    if "badrequest" in name or "client" in name or "400" in name:
        return "client_error"
    if "server" in name or "500" in name:
        return "server_error"
    if "notfound" in name or "404" in name:
        return "not_found"
    return "unknown_error"