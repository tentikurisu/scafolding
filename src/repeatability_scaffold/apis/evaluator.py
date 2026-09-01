"""API response evaluators.

- `field_equality(actual, golden)` - per-field equality report.
- `assert_matches_golden(api, behavior, actual)` - hard fail on any drift.
- `assert_schema_valid(api, raw)` - parse and validate against schema.
"""

from __future__ import annotations

from typing import Any

from .schemas import API_SCHEMAS, dump


def field_equality(actual: dict, golden: dict) -> dict[str, bool]:
    """Compare two dicts field-by-field. Returns {field: equal?}.

    Fields present in `golden` but missing from `actual` are reported as False.
    Fields present in `actual` but not in `golden` are ignored (forgiving).
    """
    report: dict[str, bool] = {}
    for key, expected in golden.items():
        if key not in actual:
            report[key] = False
        else:
            report[key] = actual[key] == expected
    return report


def all_fields_equal(actual: dict, golden: dict) -> bool:
    return all(field_equality(actual, golden).values())


def assert_schema_valid(api_name: str, raw: Any) -> Any:
    """Parse raw into the API's Pydantic schema. Raises on invalid."""
    schema = API_SCHEMAS[api_name]
    return schema.model_validate(raw)


def assert_matches_golden(
    api_name: str,
    behavior: str,
    actual: dict,
    *,
    allow_none: bool = False,
) -> dict[str, bool]:
    """Hard-fail if `actual` does not field-match the golden for (api, behavior).

    For `not_found` (None actual), `empty` ({} actual), and `error`-shaped
    behaviors, the caller should not invoke this - they have separate handling.
    """
    from ..goldens import golden_for

    if actual is None:
        if allow_none:
            return {}
        raise AssertionError(f"{api_name}/{behavior}: actual is None")

    golden = golden_for(api_name, behavior)
    if golden is None:
        # not_found golden is None - actual should also be None
        return {}

    report = field_equality(actual, golden)
    failed = [k for k, v in report.items() if not v]
    assert not failed, (
        f"{api_name}/{behavior}: field drift on {failed}\n"
        f"  actual:  {actual}\n"
        f"  golden:  {golden}"
    )
    return report


def assert_no_extra_forbidden_fields(actual: dict, forbidden: set[str]) -> None:
    """Optional helper: fail if `actual` contains any forbidden field names."""
    extras = set(actual.keys()) & forbidden
    assert not extras, f"Unexpected fields in actual: {extras}"