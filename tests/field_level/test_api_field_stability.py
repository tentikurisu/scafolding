"""API field-level stability tests (Hypothesis).

Each API stub returns a structurally consistent payload across many calls.
We generate *varied inputs* (param dicts) and assert that field-level
invariants hold (right types, right set of fields, no leakage).
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from repeatability_scaffold.apis.schemas import (
    ColorsResponse,
    NumbersResponse,
    ShapesResponse,
)
from repeatability_scaffold.apis.stubs import (
    AuthError,
    BadRequestError,
    ColorsClient,
    NumbersClient,
    ServerError,
    ShapesClient,
    TimeoutError_,
)


PARAMS_STRATEGY = st.fixed_dictionaries(
    mapping={
        "name": st.text(min_size=1, max_size=30),
    }
)


@given(params=PARAMS_STRATEGY)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_colors_successful_invariants(params):
    """For any params, a successful call returns a schema-valid ColorsResponse."""
    import asyncio
    client = ColorsClient()
    raw = asyncio.run(client.call(dict(params), behavior="successful"))
    parsed = ColorsResponse.model_validate(raw)
    assert parsed.name is not None
    assert isinstance(parsed.hex, (str, type(None)))
    if parsed.rgb is not None:
        assert all(isinstance(c, int) for c in parsed.rgb)
        assert len(parsed.rgb) == 3
    assert isinstance(parsed.complementary, (str, type(None)))
    assert isinstance(parsed.family, (str, type(None)))


@given(n=st.integers(min_value=-1000, max_value=1000))
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_numbers_successful_invariants(n):
    """For any n, a successful call returns a schema-valid NumbersResponse with n preserved."""
    import asyncio
    client = NumbersClient()
    raw = asyncio.run(client.call({"n": n}, behavior="successful"))
    parsed = NumbersResponse.model_validate(raw)
    assert parsed.n == n
    assert isinstance(parsed.is_prime, (bool, type(None)))
    assert isinstance(parsed.is_square, (bool, type(None)))
    assert parsed.parity in (None, "odd", "even")
    if parsed.factors is not None:
        assert all(isinstance(f, int) for f in parsed.factors)


@given(name=st.text(min_size=1, max_size=40))
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_shapes_successful_invariants(name):
    """For any name, a successful call returns a schema-valid ShapesResponse."""
    import asyncio
    client = ShapesClient()
    raw = asyncio.run(client.call({"name": name}, behavior="successful"))
    parsed = ShapesResponse.model_validate(raw)
    assert parsed.name is not None
    if parsed.sides is not None:
        assert isinstance(parsed.sides, int)
        assert parsed.sides >= 0
    assert isinstance(parsed.area_formula, (str, type(None)))
    assert isinstance(parsed.regular, (bool, type(None)))


@pytest.mark.parametrize(
    "client,behavior,exc_type",
    [
        (ColorsClient(), "api_400", BadRequestError),
        (ColorsClient(), "api_401_403", AuthError),
        (ColorsClient(), "api_500", ServerError),
        (ColorsClient(), "timeout", TimeoutError_),
        (NumbersClient(), "api_400", BadRequestError),
        (NumbersClient(), "api_401_403", AuthError),
        (NumbersClient(), "api_500", ServerError),
        (NumbersClient(), "timeout", TimeoutError_),
        (ShapesClient(), "api_400", BadRequestError),
        (ShapesClient(), "api_401_403", AuthError),
        (ShapesClient(), "api_500", ServerError),
        (ShapesClient(), "timeout", TimeoutError_),
    ],
)
@given(params=st.fixed_dictionaries(mapping={"name": st.text(min_size=1, max_size=20)}))
@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow])
def test_api_error_behavior_consistent_across_params(client, behavior, exc_type, params):
    """For any params, error behaviors raise the same exception type."""
    import asyncio
    raised = None
    try:
        asyncio.run(client.call(dict(params), behavior=behavior))
    except exc_type as e:
        raised = type(e).__name__
    except Exception as e:
        raised = f"WRONG:{type(e).__name__}"
    assert raised == exc_type.__name__, (
        f"{behavior} with params {params}: expected {exc_type.__name__}, got {raised}"
    )