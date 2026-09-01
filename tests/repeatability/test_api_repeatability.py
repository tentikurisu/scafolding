"""API-stage repeatability.

For each (api, successful_behavior), the stub returns the same payload across
N runs, and every field matches the golden.

For error behaviors and `not_found` (None), we verify the error class is raised
identically each time.
"""

from __future__ import annotations

import pytest

from repeatability_scaffold.apis.evaluator import (
    assert_matches_golden,
    assert_schema_valid,
    field_equality,
)
from repeatability_scaffold.apis.schemas import API_SCHEMAS
from repeatability_scaffold.apis.stubs import (
    AuthError,
    BadRequestError,
    ServerError,
    TimeoutError_,
)
from repeatability_scaffold.behaviors.catalog import (
    ERROR_BEHAVIORS,
    SUCCESS_SHAPED_BEHAVIORS,
)
from repeatability_scaffold.goldens.api_goldens import golden_for
from tests.conftest import API_NAMES, run_n_times_async


@pytest.mark.parametrize("api_name", API_NAMES)
async def test_api_successful_payload_matches_golden_n_times(api_name, api_registry, report_writer):
    """N runs of the successful-behavior call must field-match the golden."""
    client = api_registry.get(api_name)

    async def once():
        return await client.call(params={}, behavior="successful")

    results = await run_n_times_async(once, n=10)
    golden = golden_for(api_name, "successful")

    all_reports = [field_equality(r, golden) for r in results]
    # Per-field pass count across N runs:
    field_pass_counts: dict[str, int] = {}
    for report in all_reports:
        for k, v in report.items():
            field_pass_counts[k] = field_pass_counts.get(k, 0) + (1 if v else 0)

    passes = sum(1 for r in results if all(field_equality(r, golden).values()))

    report_writer(
        api=api_name,
        behavior="successful",
        stage="api_repeatability",
        passes=passes,
        total=10,
        pass_rate=passes / 10,
        field_pass_counts=field_pass_counts,
    )

    assert passes == 10, (
        f"{api_name}/successful: only {passes}/10 runs matched golden\n"
        f"  field pass counts: {field_pass_counts}"
    )


@pytest.mark.parametrize("api_name", API_NAMES)
@pytest.mark.parametrize("behavior", SUCCESS_SHAPED_BEHAVIORS)
async def test_api_success_shaped_payload_matches_golden(api_name, behavior, api_registry):
    """Each non-error behavior must match its golden."""
    client = api_registry.get(api_name)

    result = await client.call(params={}, behavior=behavior)

    if behavior == "not_found":
        assert result is None
        return

    golden = golden_for(api_name, behavior)
    actual = result or {}
    if golden is None:
        assert actual == {} or actual is None
        return
    # Two empty dicts: vacuously equal.
    if not golden and not actual:
        return
    assert field_equality(actual, golden), (
        f"{api_name}/{behavior}: drift\n  actual={result}\n  golden={golden}"
    )


@pytest.mark.parametrize("api_name", API_NAMES)
@pytest.mark.parametrize("behavior,exc_type", [
    ("api_400", BadRequestError),
    ("api_401_403", AuthError),
    ("api_500", ServerError),
    ("timeout", TimeoutError_),
])
async def test_api_error_behavior_raises_consistently(api_name, behavior, exc_type, api_registry):
    """Error behaviors raise the matching exception class N times in a row."""
    client = api_registry.get(api_name)

    errors_seen: list[str] = []

    async def once():
        try:
            await client.call(params={}, behavior=behavior)
            return None
        except Exception as exc:
            return type(exc).__name__

    results = await run_n_times_async(once, n=10)
    for r in results:
        errors_seen.append(r or "<no error>")

    # All 10 runs must raise the same exception type.
    unique = set(errors_seen)
    assert unique == {exc_type.__name__}, (
        f"{api_name}/{behavior}: expected only {exc_type.__name__}, saw {unique}"
    )


@pytest.mark.parametrize("api_name", API_NAMES)
async def test_api_successful_response_validates_schema(api_name, api_registry):
    """Successful responses must validate against the API's Pydantic schema."""
    client = api_registry.get(api_name)
    raw = await client.call(params={}, behavior="successful")
    parsed = assert_schema_valid(api_name, raw)
    assert parsed.model_config["extra"] == "ignore"  # sanity check on schema config


@pytest.mark.parametrize("api_name", API_NAMES)
async def test_api_successful_golden_field_report(api_name, api_registry):
    """Soft check: emit a per-field equality report (always True with stubs)."""
    client = api_registry.get(api_name)
    raw = await client.call(params={}, behavior="successful")
    report = assert_matches_golden(api_name, "successful", raw)
    assert all(report.values()), f"{api_name}: golden drift: {report}"