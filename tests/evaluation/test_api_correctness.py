"""API correctness evaluation.

For each API:

- Successful responses field-match the golden.
- Successful responses validate against the Pydantic schema.
- Empty/not_found/missing_field/malformed_payload are well-formed enough
  to be handled gracefully (no crashes, fields are present or None).
- Error behaviors raise the documented exception class.
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
from tests.conftest import API_NAMES


@pytest.mark.parametrize("api_name", API_NAMES)
@pytest.mark.parametrize("behavior", SUCCESS_SHAPED_BEHAVIORS)
async def test_api_response_is_correct_for_behavior(api_name, behavior, api_registry):
    client = api_registry.get(api_name)
    result = await client.call(params={}, behavior=behavior)

    if behavior == "not_found":
        assert result is None, f"{api_name}/not_found should return None, got {result!r}"
        return

    golden = golden_for(api_name, behavior)
    # Golden may be empty dict for empty behavior.
    if golden is None:
        # Should not happen - empty golden is {}, not None
        assert result == {} or result is None
        return

    report = field_equality(result or {}, golden)
    failed = [k for k, v in report.items() if not v]
    assert not failed, (
        f"{api_name}/{behavior}: field drift on {failed}\n"
        f"  actual: {result}\n  golden: {golden}"
    )


@pytest.mark.parametrize("api_name", API_NAMES)
@pytest.mark.parametrize("behavior", SUCCESS_SHAPED_BEHAVIORS)
async def test_api_response_schema_valid_for_behavior(api_name, behavior, api_registry):
    """Success-shaped behaviors must parse against the schema (or be None)."""
    client = api_registry.get(api_name)
    result = await client.call(params={}, behavior=behavior)

    if behavior == "not_found":
        assert result is None
        return

    schema = API_SCHEMAS[api_name]
    # Empty payloads validate as the schema with all None fields.
    # Malformed payloads intentionally fail validation in the lambda, not here.
    if behavior == "malformed_payload":
        # Stub returns wrong types; schema validation must raise.
        with pytest.raises(Exception):
            schema.model_validate(result)
    else:
        parsed = schema.model_validate(result)
        assert parsed is not None


@pytest.mark.parametrize("api_name", API_NAMES)
@pytest.mark.parametrize("behavior,exc_type", [
    ("api_400", BadRequestError),
    ("api_401_403", AuthError),
    ("api_500", ServerError),
    ("timeout", TimeoutError_),
])
async def test_api_error_behavior_raises_correct_exception(api_name, behavior, exc_type, api_registry):
    client = api_registry.get(api_name)
    with pytest.raises(exc_type):
        await client.call(params={}, behavior=behavior)


@pytest.mark.parametrize("api_name", API_NAMES)
async def test_api_golden_is_complete(api_name):
    """Every behavior we test must have a golden entry."""
    from repeatability_scaffold.behaviors.catalog import BEHAVIORS

    for behavior in BEHAVIORS:
        # not_found goldens are None - that's a valid entry.
        golden = golden_for(api_name, behavior)
        if behavior == "not_found":
            assert golden is None
        elif behavior in ERROR_BEHAVIORS:
            # Error behaviors don't have a "payload" golden.
            continue
        else:
            assert isinstance(golden, dict)


@pytest.mark.parametrize("api_name", API_NAMES)
async def test_api_successful_matches_golden_hard(api_name, api_registry):
    """Direct hard-fail comparison: actual must match golden field-by-field."""
    client = api_registry.get(api_name)
    raw = await client.call(params={}, behavior="successful")
    report = assert_matches_golden(api_name, "successful", raw)
    assert all(report.values()), f"{api_name}: golden drift: {report}"


@pytest.mark.parametrize("api_name", API_NAMES)
async def test_api_response_uses_correct_schema_class(api_name, api_registry):
    """Successful response parses to the right schema class."""
    from repeatability_scaffold.apis.schemas import schema_for

    client = api_registry.get(api_name)
    raw = await client.call(params={}, behavior="successful")
    parsed = assert_schema_valid(api_name, raw)
    assert type(parsed) is schema_for(api_name)