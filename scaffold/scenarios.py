"""Central scenario definitions.

One source of truth for all test scenarios. Tests parametrize over this
collection; adding a new scenario means appending one Scenario object here,
not editing multiple test files.

The fictional colors/numbers/shapes examples preserve the spirit of the
original scaffold. Replace them with real business scenarios when available.
"""

from __future__ import annotations

from .models import Scenario


def _scn(**kwargs) -> Scenario:
    """Helper: build a Scenario with sensible defaults."""
    return Scenario(**kwargs)


# === Fictional example scenarios =====================================
# These illustrate the structure. Replace with real scenarios derived from
# requirements and API contracts, not from observed LLM output.

# Successful reads across the 3 example APIs
_SUCCESS = {
    "fetch_red": _scn(
        name="fetch_red",
        prompt="describe the color red",
        behavior="successful",
        expected_target_api="colors",
        expected_tool_parameters={"name": "red"},
        expected_response_tokens=["red", "#FF0000"],
        forbidden_response_tokens=[],
        expected_api_fields={"name": "red", "hex": "#FF0000"},
        supports_real_target=True,
        notes="Happy path: look up a known color.",
    ),
    "check_17": _scn(
        name="check_17",
        prompt="is 17 prime?",
        behavior="successful",
        expected_target_api="numbers",
        expected_tool_parameters={"n": 17},
        expected_response_tokens=["17", "prime"],
        forbidden_response_tokens=[],
        expected_api_fields={"n": 17, "is_prime": True},
        supports_real_target=True,
        notes="Happy path: check a number property.",
    ),
    "describe_pentagon": _scn(
        name="describe_pentagon",
        prompt="describe a pentagon",
        behavior="successful",
        expected_target_api="shapes",
        expected_tool_parameters={"name": "pentagon"},
        expected_response_tokens=["pentagon"],
        forbidden_response_tokens=[],
        expected_api_fields={"name": "pentagon", "sides": 5},
        supports_real_target=True,
        notes="Happy path: describe a known shape.",
    ),
}

# Safe-to-run-against-real scenarios (no fault injection).
_REAL_SAFE = {
    "fetch_red_not_found": _scn(
        name="fetch_red_not_found",
        prompt="look up color xyz_not_a_real_color",
        behavior="not_found",
        expected_target_api="colors",
        expected_tool_parameters={"name": "xyz_not_a_real_color"},
        expected_response_tokens=["not found"],
        forbidden_response_tokens=["#FF0000", "rgb"],
        expected_error_category="not_found",
        minimum_pass_rate=0.9,
        supports_real_target=True,
        notes="Real-safe: a guaranteed-unknown identifier should never invent data.",
    ),
    "fetch_red_empty": _scn(
        name="fetch_red_empty",
        prompt="look up color with empty search",
        behavior="empty",
        expected_target_api="colors",
        expected_tool_parameters={},
        expected_response_tokens=["unavailable"],
        forbidden_response_tokens=["#FF0000"],
        expected_error_category="empty",
        supports_real_target=True,
        notes="Real-safe: empty input produces an empty result.",
    ),
}

# Mock-only scenarios (fault injection; skipped on real Lambda target).
_MOCK_ONLY = {
    "fetch_red_api_400": _scn(
        name="fetch_red_api_400",
        prompt="describe the color red",
        behavior="api_400",
        expected_response_tokens=["invalid"],
        expected_error_category="client_error",
        supports_real_target=False,
        notes="Mock-only: forces a simulated 400. Real APIs won't do this on demand.",
    ),
    "fetch_red_api_500": _scn(
        name="fetch_red_api_500",
        prompt="describe the color red",
        behavior="api_500",
        expected_response_tokens=["error", "service"],
        expected_error_category="server_error",
        supports_real_target=False,
        notes="Mock-only: forces a simulated 500.",
    ),
    "fetch_red_timeout": _scn(
        name="fetch_red_timeout",
        prompt="describe the color red",
        behavior="timeout",
        expected_response_tokens=["unavailable"],
        expected_error_category="timeout",
        supports_real_target=False,
        notes="Mock-only: forces a simulated timeout.",
    ),
    "fetch_red_malformed": _scn(
        name="fetch_red_malformed",
        prompt="describe the color red",
        behavior="malformed_payload",
        expected_response_tokens=["unexpected"],
        forbidden_response_tokens=["rgb"],
        supports_real_target=False,
        notes="Mock-only: returns a corrupt payload to test schema tolerance.",
    ),
}


ALL_SCENARIOS: list[Scenario] = (
    list(_SUCCESS.values())
    + list(_REAL_SAFE.values())
    + list(_MOCK_ONLY.values())
)


def scenarios_for_target(test_target: str) -> list[Scenario]:
    """Return scenarios appropriate for the given TEST_TARGET.

    Mock target gets all scenarios. Real Lambda target excludes mock_only ones.
    """
    if test_target == "lambda":
        return [s for s in ALL_SCENARIOS if s.supports_real_target]
    return list(ALL_SCENARIOS)


def by_name(name: str) -> Scenario | None:
    """Lookup a scenario by name (first match across all behaviors)."""
    for s in ALL_SCENARIOS:
        if s.name == name:
            return s
    return None