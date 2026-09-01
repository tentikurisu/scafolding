"""Golden API responses per (api, behavior).

The single source of truth for "what the API should return" given a behavior.
Repeatability and correctness tests compare against these.

To record real responses: capture one happy-path response per API, drop it in
here, and run `tests/repeatability/test_api_repeatability.py`.
"""

from __future__ import annotations

from typing import Any


API_GOLDENS: dict[tuple[str, str], dict[str, Any] | None] = {
    # colors
    ("colors", "successful"): {
        "name": "red",
        "hex": "#FF0000",
        "rgb": [255, 0, 0],
        "family": "red",
        "complementary": "#00FFFF",
    },
    ("colors", "empty"): {},
    ("colors", "not_found"): None,
    ("colors", "missing_field"): {"name": "red", "hex": "#FF0000"},
    ("colors", "malformed_payload"): {"name": "red", "hex": 12345, "rgb": "not-a-list"},
    ("colors", "api_400"): None,
    ("colors", "api_401_403"): None,
    ("colors", "api_500"): None,
    ("colors", "timeout"): None,
    # numbers
    ("numbers", "successful"): {
        "n": 17,
        "is_prime": True,
        "is_square": False,
        "parity": "odd",
        "factors": [1, 17],
    },
    ("numbers", "empty"): {},
    ("numbers", "not_found"): None,
    ("numbers", "missing_field"): {"n": 17, "is_prime": True},
    ("numbers", "malformed_payload"): {"n": "seventeen", "is_prime": "yes"},
    ("numbers", "api_400"): None,
    ("numbers", "api_401_403"): None,
    ("numbers", "api_500"): None,
    ("numbers", "timeout"): None,
    # shapes
    ("shapes", "successful"): {
        "name": "pentagon",
        "sides": 5,
        "area_formula": "(1/4) * sqrt(5*(5+2*sqrt(5))) * a^2",
        "regular": True,
    },
    ("shapes", "empty"): {},
    ("shapes", "not_found"): None,
    ("shapes", "missing_field"): {"name": "pentagon", "sides": 5},
    ("shapes", "malformed_payload"): {"name": "pentagon", "sides": "five"},
    ("shapes", "api_400"): None,
    ("shapes", "api_401_403"): None,
    ("shapes", "api_500"): None,
    ("shapes", "timeout"): None,
}


def golden_for(api_name: str, behavior: str) -> dict[str, Any] | None:
    if (api_name, behavior) not in API_GOLDENS:
        raise KeyError(f"No golden for ({api_name!r}, {behavior!r})")
    return API_GOLDENS[(api_name, behavior)]