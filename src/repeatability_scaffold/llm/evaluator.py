"""LLM response evaluators.

Provides:

- `validate_llm_response(raw)` - parse a raw dict into `LLMResponse`.
- `free_text_fields(response)` - return concatenated free-text strings.
- `jaccard_similarity(responses)` - token-set Jaccard across N responses.
- `assert_concise(response, ...)` - hard gate on length / required fields.
"""

from __future__ import annotations

import re
from typing import Iterable

from .schemas import LLMResponse


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(s: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(s)}


def validate_llm_response(raw: dict) -> LLMResponse:
    """Parse and validate a raw LLM dict. `extra="ignore"` is forgiving."""
    return LLMResponse.model_validate(raw)


def free_text_fields(response: LLMResponse | dict | str) -> str:
    """Concatenate all free-text fields. Used as the input to Jaccard."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        response = validate_llm_response(response)
    return " ".join(
        str(response.reasoning or ""),
    )


def jaccard_similarity(responses: Iterable[dict | LLMResponse | str]) -> float:
    """Token-set Jaccard over the concatenation of free-text fields.

    With deterministic stubs this should always be 1.0. The check is meaningful
    once a real LLM is plugged in: it surfaces drift in free-text fields.

    Returns 1.0 if all inputs are empty (degenerate but safe).
    """
    token_sets: list[set[str]] = []
    for r in responses:
        token_sets.append(_tokens(free_text_fields(r)))

    if not token_sets:
        return 1.0

    union: set[str] = set()
    intersect: set[str] | None = None
    for ts in token_sets:
        union |= ts
        if intersect is None:
            intersect = set(ts)
        else:
            intersect &= ts

    if intersect is None:
        intersect = set()

    if not union:
        return 1.0
    return len(intersect) / len(union)


def assert_concise(
    response: LLMResponse | dict,
    *,
    max_chars: int = 500,
    required_fields: tuple[str, ...] = ("action", "target_api", "params"),
) -> None:
    """Hard gate: required fields present, free-text within length bounds."""
    if isinstance(response, dict):
        response = validate_llm_response(response)

    missing = [f for f in required_fields if not getattr(response, f, None)]
    assert not missing, f"LLM response missing required fields: {missing}"

    assert (
        len(response.reasoning) <= max_chars
    ), f"reasoning too long ({len(response.reasoning)} chars > {max_chars})"