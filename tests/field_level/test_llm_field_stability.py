"""LLM field-level stability tests (Hypothesis).

Hypothesis generates varied prompt inputs; we assert that structural
invariants of the LLMResponse hold across all variations:

- `target_api` is always one of the registered APIs.
- `action` is always a known action.
- `params` is always a dict.
- `reasoning` is always a string within length bounds.
- The LLMResponse parses via Pydantic (extra="ignore" tolerates extras).

These are *invariants*, not equality checks: even when prompts vary widely,
the schema shape stays valid.
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings, strategies as st

from repeatability_scaffold.llm.evaluator import validate_llm_response
from repeatability_scaffold.llm.schemas import VALID_ACTIONS, VALID_TARGET_APIS
from repeatability_scaffold.llm.stub_provider import STUB_RESPONSES


# Strategy: any unicode string up to a reasonable length.
PROMPT_STRATEGY = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S", "Z"),
        max_codepoint=0x7E,
    ),
    min_size=0,
    max_size=200,
)


@given(prompt=PROMPT_STRATEGY, scenario=st.sampled_from(list(STUB_RESPONSES.keys())))
@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
def test_llm_response_invariants_hold_for_any_prompt(prompt, scenario):
    """Across many prompt variations, structural invariants hold."""
    # The stub is deterministic by scenario, not by prompt - so we still
    # need to actually invoke the LLM through the client interface.
    from repeatability_scaffold.pipeline.llm_client import LLMClient
    import asyncio

    client = LLMClient()
    raw = asyncio.run(client.ask(prompt, scenario))
    parsed = validate_llm_response(raw)

    # Required fields are present and well-typed.
    assert isinstance(parsed.action, str)
    assert isinstance(parsed.target_api, str)
    assert isinstance(parsed.params, dict)
    assert isinstance(parsed.reasoning, str)

    # Membership invariants.
    assert parsed.action in VALID_ACTIONS
    assert parsed.target_api in VALID_TARGET_APIS

    # Length invariants.
    assert len(parsed.reasoning) <= 1000
    assert len(parsed.action) <= 32
    assert len(parsed.target_api) <= 32


@given(scenario=st.sampled_from(list(STUB_RESPONSES.keys())))
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_llm_decision_is_in_registry_for_any_scenario(scenario):
    """target_api in LLMDecision is always present in the API registry."""
    from repeatability_scaffold.pipeline.api_registry import build_default_registry
    import asyncio
    from repeatability_scaffold.pipeline.llm_client import LLMClient

    client = LLMClient()
    raw = asyncio.run(client.ask("anything", scenario))
    parsed = validate_llm_response(raw)

    registry = build_default_registry()
    assert parsed.target_api in registry, (
        f"scenario {scenario!r} LLM picked {parsed.target_api!r} which is not registered"
    )


@given(
    extras=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans(), st.none()),
        max_size=5,
    )
)
@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
def test_llm_response_tolerates_extra_fields(extras):
    """`extra="ignore"` should let us tack on unknown fields without breaking validation."""
    from repeatability_scaffold.llm.schemas import LLMResponse

    base = {
        "action": "fetch",
        "target_api": "colors",
        "params": {"name": "red"},
        "reasoning": "ok",
    }
    raw = {**base, **extras}
    parsed = LLMResponse.model_validate(raw)
    # Required fields preserved.
    assert parsed.action == "fetch"
    assert parsed.target_api == "colors"
    assert parsed.params == {"name": "red"}
    assert parsed.reasoning == "ok"
    # Extras are silently ignored.
    assert not hasattr(parsed, list(extras.keys())[0]) if extras else True