"""Tools to assess LLM and API responses.

Drop into your repo's `tests/` folder. Import the functions you need.

Examples:

    from validators import (
        validate_llm_response, contains_all, jaccard,
        validate_api_response, fields_match,
        run_n_async_times,
    )

    # Assess LLM response
    raw = await your_llm.ask(prompt, scenario)
    parsed = validate_llm_response(raw)
    assert contains_all(parsed.reasoning, ["red", "hex"])

    # Run N times and check similarity
    results = await run_n_async_times(lambda: your_llm.ask(prompt, scenario))
    assert jaccard(r["reasoning"] for r in results) >= 0.95

    # Assess API response
    parsed = validate_api_response(raw, YourAPIResponse)
    assert fields_match(parsed.model_dump(), {"name": "red", "hex": "#FF0000"})
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Awaitable, Callable, Iterable

from pydantic import BaseModel, ConfigDict


# === LLM response schema =============================================

class LLMResponse(BaseModel):
    """Generic LLM decision schema. `extra="ignore"` is forgiving."""
    model_config = ConfigDict(extra="ignore")
    action: str = ""
    target_api: str = ""
    params: dict[str, Any] = {}
    reasoning: str = ""


def validate_llm_response(raw: dict) -> LLMResponse:
    """Parse and validate a raw LLM dict. Raises on invalid."""
    return LLMResponse.model_validate(raw)


# === Content checks ==================================================

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def contains_all(text: str, tokens: Iterable[str]) -> bool:
    """True iff every token appears in `text` (case-insensitive substring)."""
    return all(t.lower() in text.lower() for t in tokens)


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


# === API response checks =============================================

def validate_api_response(raw: dict, schema: type[BaseModel]) -> BaseModel:
    """Parse raw dict into the API's Pydantic schema. Raises on invalid."""
    return schema.model_validate(raw)


def fields_match(actual: dict, expected: dict) -> bool:
    """True iff every field in `expected` exists in `actual` with the same value.
    Extra fields in `actual` are ignored (forgiving)."""
    return all(actual.get(k) == v for k, v in expected.items())


def fields_match_report(actual: dict, expected: dict) -> dict[str, bool]:
    """Per-field equality report."""
    return {k: actual.get(k) == v for k, v in expected.items()}


# === Run-N-times helpers ============================================

async def run_n_async_times(
    coro_factory: Callable[[], Awaitable],
    n: int = 10,
) -> list:
    """Run an async no-arg callable N times."""
    return [await coro_factory() for _ in range(n)]


def run_n_times(fn: Callable, *args: Any, n: int = 10, **kwargs) -> list:
    """Run a sync callable N times with the same args."""
    return [fn(*args, **kwargs) for _ in range(n)]