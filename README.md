# Repeatability Scaffold

A scaffold for testing repeatability across an **LLM → execution lambda → API** chain.

```
[user prompt] → [LLM decision] → [execution lambda] → [API call(s)] → [agent message]
```

The point of the scaffold is **easy plug-in**. The LLM and APIs are stubbed by
default. To swap in real implementations, you create a new provider module and
flip an env var. **No test code or pipeline code changes.**

---

## Validation Model

Agent responses are validated by **token containment**:

- For each `(scenario, behavior)`, define the **required tokens**.
- The check is plain case-insensitive substring matching.
- For example: `("fetch_color_red", "successful") -> ["red", "#FF0000"]`
  asserts the agent_message contains both `"red"` and `"#FF0000"`.
- Optional **groups** allow alternative token combinations: at least one
  group's tokens must all appear.

See `src/repeatability_scaffold/behaviors/expected_responses.py`.

```python
from repeatability_scaffold.behaviors.expected_responses import matches_expected

ok, reason = matches_expected(agent_message, "fetch_color_red", "successful")
```

---

## Configuration

Everything configurable lives in **`repeatability.yaml`** at the project root.

```yaml
llm:        # which LLM provider to use, plus provider-specific config
apis:       # which API client per API (stub | http), plus base URLs
behaviors:  # the placeholder behaviors tested against each scenario
tests:      # N runs, thresholds, report directory
scenarios:  # per-scenario prompts, params, stub responses, expectations
```

Edit this file to:

- Change `llm.provider: stub` → `bedrock` to swap LLM
- Change `apis.colors.type: stub` → `http` to use real HTTP
- Add a new scenario under `scenarios:`
- Change what each test expects (`scenarios.<name>.expectations.<behavior>`)
- Change what each test sends (`scenarios.<name>.prompt` / `params`)

**No Python code changes required.**

See the file for the full schema with comments. Load it from a different
path with `REPEATABILITY_CONFIG=/path/to/other.yaml pytest`.

Verify your config is being picked up:

```bash
python -m spikes.spike_config
```

If the file is missing, every module falls back to the Python defaults.

---

## Stack

- **Language**: Python 3.10+ (async)
- **Tests**: pytest + pytest-asyncio + Hypothesis
- **Schemas**: Pydantic v2 (`extra="ignore"` for forgiveness)
- **Reports**: per-run JSON summary in `reports/`

---

## Swap-In: Real LLM (AWS Bedrock)

The stub provider is the default. To switch to AWS Bedrock:

1. **Install the Bedrock extra**:

   ```bash
   pip install -e ".[bedrock]"
   ```

2. **Configure AWS** (any method supported by boto3 works):

   ```bash
   export AWS_REGION=us-east-1
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   ```

3. **Set the provider**:

   ```bash
   export LLM_PROVIDER=bedrock
   ```

4. **Run the same tests**:

   ```bash
   pytest -q
   python -m spikes.spike_evaluate
   ```

That's it. The pipeline, validators, and test assertions all run unchanged.

### How it works under the hood

- `src/repeatability_scaffold/llm/providers/bedrock_provider.py` implements
  the `ProviderProtocol` (two async functions: `first_call`, `second_call`).
- It uses Bedrock's `converse` API with **tool use** to force structured
  output matching `LLMResponse`. temperature=0 by default.
- Returns the **same dict shape** as the stub provider.
- Lazy import: if `aioboto3` isn't installed, the stub stays the default.

---

## Adding Your Own Provider

Create a new file `src/repeatability_scaffold/llm/providers/<name>.py`:

```python
from typing import Any

class MyProvider:
    async def first_call(self, prompt: str, scenario: str) -> dict[str, Any]:
        # Call your real LLM. Return a dict like:
        # {"action": "...", "target_api": "...", "params": {...}, "reasoning": "..."}
        ...

    async def second_call(
        self,
        scenario: str,
        behavior: str,
        api_response: dict | None,
        api_error: str | None,
    ) -> str:
        # Call your real LLM with the API response. Return a string.
        ...
```

Register it in `providers/__init__.py`:

```python
def _build_my() -> ProviderProtocol:
    return MyProvider()

register_provider("my", _build_my)
```

Use it: `LLM_PROVIDER=my pytest`.

The test suite and pipeline never change.

---

## Swap-In: Real APIs (future)

The same pattern applies for API clients. Today the three stubbed APIs
(`colors`, `numbers`, `shapes`) live in `apis/stubs.py`. To swap in real
HTTP-backed clients:

1. Create `src/repeatability_scaffold/apis/clients/<name>.py`:

   ```python
   import httpx

   class ColorsClient:
       name = "colors"

       async def call(self, params: dict, behavior: str) -> dict | None:
           async with httpx.AsyncClient(base_url=API_BASE_URL) as http:
               r = await http.get(f"/colors/{params['name']}")
               r.raise_for_status()
               return r.json()
   ```

2. Update `apis/registry.py` (or the `build_default_registry()` factory) to
   pick the real or stub client based on env.

3. Tests run unchanged.

For failure-mode testing (400/401/500/timeout), keep the stubs as a
fault-injection layer behind a flag, or stand up a wiremock server.

---

## Behavior Matrix

For each scenario, the API stub can simulate 9 placeholder behaviors:

| Behavior | Agent expected to (token must appear in response) |
|----------|---------------------------------------------------|
| `successful` | `red`, `#FF0000` (use the returned data) |
| `empty` | `unavailable` |
| `not_found` | `not found` |
| `missing_field` | `partial` (or scenario-specific) |
| `malformed_payload` | `unexpected` |
| `api_400` | `invalid request` |
| `api_401_403` | `access` |
| `api_500` | `service`, `error` |
| `timeout` | `unavailable` |

See `src/repeatability_scaffold/behaviors/expected_responses.py` for the
full token list per `(scenario, behavior)`.

---

## Repeatability Bar

- **Default N=10** runs per scenario (configurable via `N_RUNS`).
- **100% pass rate** required: every run's tokens must all appear.
- **Jaccard ≥ 0.95** on LLM free-text fields.

---

## Install / Run

```bash
pip install -e ".[dev]"          # core + test deps
pip install -e ".[bedrock]"      # optional: Bedrock provider
pip install -e ".[http]"         # optional: real HTTP clients

pytest                              # full suite
pytest -q tests/repeatability       # repeatability only
pytest -q tests/behavior            # behavior matrix only
pytest -q tests/field_level         # Hypothesis field-stability only
pytest -q tests/evaluation          # conciseness + correctness only
```

---

## Spikes

```bash
python -m spikes.spike_send_receive_llm
python -m spikes.spike_send_receive_api
python -m spikes.spike_evaluate
python -m spikes.spike_config                   # show loaded config
python -m spikes.spike_provider                 # default = stub
python -m spikes.spike_provider --provider bedrock
```

---

## Reports

Every `pytest` run writes `reports/run-<UTC-timestamp>.json` with:

- Top-level totals (pass/fail/pass rate)
- Per-test extras (`passes`, `total`, `pass_rate`, `jaccard`, `field_pass_counts`)

Disable by setting `REPORT_DIR=` (empty) in env.

---

## Directory Layout

```
repeatability.yaml           # single source of truth for all config
src/repeatability_scaffold/
├── config.py            YAML loader + accessors
├── pipeline/             LLMClient, ExecutionLambda, APIClientRegistry
├── llm/
│   ├── schemas.py        LLMResponse (extra="ignore")
│   ├── stub_provider.py  StubProvider (deterministic, default)
│   ├── evaluator.py      validate / jaccard / concise gates
│   └── providers/
│       ├── __init__.py   Provider registry + dispatch
│       └── bedrock_provider.py   AWS Bedrock implementation
├── apis/
│   ├── schemas.py        Pydantic per-API response models
│   ├── stubs.py          3 stubbed API clients
│   ├── evaluator.py      field equality vs golden
│   └── clients/
│       └── http.py       HTTP-backed clients (type: http in config)
├── behaviors/            9-behavior catalog + token-containment expectations
└── goldens/              Per-(api, behavior) golden payloads
```