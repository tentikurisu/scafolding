"""Usage examples for validators.py — drop into your tests/ folder.

These are not a "test suite", just demonstrations of how to use the
helpers. Adapt to your real LLM and API calls.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from validators import (
    contains_all,
    fields_match,
    fields_match_report,
    jaccard,
    run_n_async_times,
    run_n_times,
    validate_api_response,
    validate_llm_response,
)


# === Example schema for an API response =============================

class ColorResponse(BaseModel):
    name: str | None = None
    hex: str | None = None
    rgb: list[int] | None = None


# === LLM response: schema + content ==================================

def test_llm_response_parses_and_has_required_fields():
    raw = {
        "action": "fetch",
        "target_api": "colors",
        "params": {"name": "red"},
        "reasoning": "Looking up color information for red.",
    }
    parsed = validate_llm_response(raw)
    assert parsed.action == "fetch"
    assert parsed.target_api == "colors"
    assert parsed.params == {"name": "red"}


def test_llm_response_tolerates_unknown_fields():
    raw = {"action": "fetch", "target_api": "colors", "params": {},
           "reasoning": "x", "extra_unknown_field": "ignored"}
    parsed = validate_llm_response(raw)  # does not raise
    assert parsed.action == "fetch"


def test_contains_all_substring_match():
    msg = "Red has hex code #FF0000 and complementary cyan."
    assert contains_all(msg, ["red", "#FF0000"])
    assert contains_all(msg, ["RED", "hex"])  # case-insensitive
    assert not contains_all(msg, ["blue"])


# === LLM response: repeatability via Jaccard =========================

def test_jaccard_identical_texts_score_one():
    texts = ["Red is #FF0000", "Red is #FF0000", "Red is #FF0000"]
    assert jaccard(texts) == 1.0


def test_jaccard_divergent_texts_score_lower():
    texts = ["Red is #FF0000", "Blue is #0000FF", "Green is #00FF00"]
    score = jaccard(texts)
    assert 0.0 <= score < 0.5


def test_run_n_times_sync():
    def double(x):
        return x * 2
    results = run_n_times(double, 5, n=3)
    assert results == [10, 10, 10]


# === API response: schema + field equality ==========================

def test_api_response_validates_against_schema():
    raw = {"name": "red", "hex": "#FF0000", "rgb": [255, 0, 0]}
    parsed = validate_api_response(raw, ColorResponse)
    assert parsed.name == "red"
    assert parsed.hex == "#FF0000"


def test_fields_match():
    actual = {"name": "red", "hex": "#FF0000", "rgb": [255, 0, 0], "extra": "ignored"}
    assert fields_match(actual, {"name": "red", "hex": "#FF0000"})
    assert not fields_match(actual, {"name": "blue"})


def test_fields_match_report():
    actual = {"name": "red", "hex": "#FF0000", "rgb": [999, 0, 0]}
    report = fields_match_report(actual, {"name": "red", "hex": "#FFFFFF", "rgb": [255, 0, 0]})
    assert report == {"name": True, "hex": False, "rgb": False}


# === Async helper (requires pytest-asyncio) =========================

@pytest.mark.skip(reason="Enable by adding 'pytest-asyncio' and removing this skip")
def test_run_n_async_times_pattern():
    """Example of how you'd assess your real LLM across N runs.
    Enable by installing pytest-asyncio and removing the @pytest.mark.skip.
    """
    import asyncio

    async def fake_ask(prompt):
        # Replace with: await your_real_llm.ask(prompt)
        return {"action": "fetch", "target_api": "colors",
                "params": {"name": "red"}, "reasoning": "ok"}

    async def main():
        results = await run_n_async_times(lambda: fake_ask("describe red"))
        parsed = [validate_llm_response(r) for r in results]
        assert jaccard(p.reasoning for p in parsed) >= 0.99
        for p in parsed:
            assert contains_all(p.reasoning, ["ok"])

    asyncio.run(main())