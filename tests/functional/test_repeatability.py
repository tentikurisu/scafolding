"""Functional repeatability tests across scenarios."""
import pytest
from scaffold.scenarios import scenarios_for_target
from scaffold.config import get_config
from scaffold.validators import jaccard, contains_all


pytestmark = pytest.mark.functional


def _safe_scenarios():
    """Return scenarios safe to repeat against either target."""
    return scenarios_for_target(get_config().test_target)


@pytest.mark.parametrize(
    "scenario",
    _safe_scenarios(),
    ids=[f"{s.name}-{s.behavior}" for s in _safe_scenarios()],
)
async def test_response_text_jaccard_above_threshold(scenario, system_under_test):
    """Across N runs, free-text Jaccard should remain high."""
    n = min(scenario.run_count, 5)  # cap to keep functional tests fast
    texts = []
    for _ in range(n):
        result = await system_under_test.invoke(
            scenario.prompt, scenario=scenario.name, behavior=scenario.behavior,
        )
        texts.append(result.response_text)

    # For mock target, Jaccard should be 1.0 (deterministic).
    # For real Lambda target, we don't enforce Jaccard on free text (real LLMs drift).
    cfg = get_config()
    if cfg.test_target == "mock":
        assert jaccard(texts) == 1.0, f"{scenario.name}: not deterministic"


@pytest.mark.parametrize(
    "scenario",
    _safe_scenarios(),
    ids=[f"{s.name}-{s.behavior}" for s in _safe_scenarios()],
)
async def test_required_tokens_present_in_every_run(scenario, system_under_test):
    """For required tokens, every run must include them (no occasional drops)."""
    if not scenario.expected_response_tokens:
        pytest.skip("No required tokens")
    n = min(scenario.run_count, 5)
    for _ in range(n):
        result = await system_under_test.invoke(
            scenario.prompt, scenario=scenario.name, behavior=scenario.behavior,
        )
        assert contains_all(result.response_text, scenario.expected_response_tokens), (
            f"{scenario.name}: a run missed required tokens: {result.response_text!r}"
        )