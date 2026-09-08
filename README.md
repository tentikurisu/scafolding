# Test Harness for an LLM-driven Execution Lambda

A small test harness designed to be copied into another repository
that already contains the production Lambda handler, LLM integration,
and API clients.

The harness **invokes the real production handler** with mocked
dependencies for local tests, and the **deployed Lambda** for end-to-end
tests. It does NOT recreate orchestration logic.

---

## Files (drop these into your repo's `tests/` folder)

```
tests/
├── conftest.py                    fixtures + marker configuration
├── unit/
│   └── test_assertions.py         unit tests for the assertion function
└── functional/
    ├── scenarios.py               central Scenario dataclass + list
    ├── assertions.py              assert_scenario(result, scenario)
    ├── project_adapter.py         FOUR functions to adapt (see below)
    ├── mocks.py                   ConfigurableMockAPI (one generic class)
    ├── test_local_handler.py      local tests against real handler + mocks
    └── test_deployed_lambda.py    deployed tests (opt-in)

pyproject.toml                     test deps + pytest markers
.env.example                       placeholder env vars
README.md                          this file
```

## Three test levels

| Marker | Target | When it runs | AWS/LLM cost |
|---|---|---|---|
| `unit` | `assert_scenario` function | every pytest run | None |
| `functional` | real handler + mocks | every pytest run | None |
| `deployed` | deployed AWS Lambda | only when opted in | Lambda + LLM + APIs |

## Commands

```bash
# Install (no AWS, no httpx)
pip install -e ".[test]"

# Run everything locally — no AWS contact
pytest

# Just unit tests
pytest -m unit

# Just local functional tests
pytest -m "functional and not deployed"

# Opt into deployed Lambda tests
RUN_DEPLOYED_FUNCTIONAL_TESTS=true \
EXECUTION_LAMBDA_NAME=my-execution-lambda \
AWS_REGION=us-east-1 \
pytest -m deployed
```

An ordinary `pytest` run never contacts AWS or any external API.

## The four functions to adapt in `tests/functional/project_adapter.py`

This is the ONLY file that normally needs structural editing after the
harness is copied into your repository.

### 1. `load_production_handler()`

Returns your real Lambda handler. Two options:

```python
# Option A: import directly (recommended)
from my_project.execution import lambda_handler
return lambda_handler
```

```python
# Option B: load from env at runtime
EXECUTION_HANDLER_PATH=my_project.execution:lambda_handler
```

### 2. `build_lambda_event(scenario)`

Translates a `Scenario` into the event shape your Lambda expects.

```python
def build_lambda_event(scenario) -> dict:
    return {"prompt": scenario.question, "user_id": "test-user"}
```

### 3. `normalize_response(raw)`

Translates the raw Lambda response into the harness's `ExecutionResult`.
The harness asserts on this normalized shape — fields it doesn't find
are skipped, not failed.

```python
def normalize_response(raw):
    return ExecutionResult(
        answer_text=raw["answer"],
        target_api=raw.get("trace", {}).get("tool"),
        tool_parameters=raw.get("trace", {}).get("arguments"),
        api_response=raw.get("trace", {}).get("api_response"),
        api_error=raw.get("error"),
        raw_response=raw,
    )
```

### 4. `install_test_dependencies(monkeypatch, mocks)`

Patches your production LLM/API factories so the handler uses mocks.
This is the only function that knows how your production code is wired.

```python
# Example for module-level factories:
def install_test_dependencies(monkeypatch, mocks):
    monkeypatch.setattr("my_project.execution.create_llm",
                        lambda: mocks["llm"])
    monkeypatch.setattr("my_project.execution.create_api_registry",
                        lambda: mocks["registry"])
```

```python
# Example for a class-based handler:
def install_test_dependencies(monkeypatch, mocks):
    monkeypatch.setattr(MyHandler, "create_llm",
                        classmethod(lambda cls: mocks["llm"]))
```

The expected ideal production shape:

```python
def lambda_handler(event, context):
    return execute(
        event,
        llm=create_llm(),
        api_registry=create_api_registry(),
    )

def execute(event, llm, api_registry):
    # ... real orchestration ...
```

If your handler can't inject deps this cleanly, `install_test_dependencies`
should use `monkeypatch.setattr` to swap whatever the handler calls.

## How tests work

```python
async def test_scenario_against_actual_handler(scenario, handler, fake_context, monkeypatch):
    # 1. Build mocks from the scenario.
    mocks = _make_mocks(scenario)

    # 2. Patch production dependencies.
    install_test_dependencies(monkeypatch, mocks)

    # 3. Run the real production handler.
    event = build_lambda_event(scenario)
    raw = await handler(event, fake_context)

    # 4. Normalize + assert.
    result = normalize_response(raw)
    assert_scenario(result, scenario)

    # 5. Verify the request actually reached the API (not just what LLM said).
    assert mocks["api"].calls[-1] == scenario.expected_api_request
```

## Adding a scenario

In `tests/functional/scenarios.py`:

```python
Scenario(
    name="fetch_user_profile",
    question="look up user alice",
    expected_api_name="users",
    expected_api_request={"user_id": "alice"},
    mock_api_response={"id": "alice", "name": "Alice"},
    expected_answer_tokens=("Alice",),
)
```

That's it — no edits to test files, assertion function, or mocks.

## Replacing a fictional API contract with a real one

The fictional examples use a `records` API with `asset_id` / `currentStatus`.
To replace with a real API:

1. Add the real `Scenario(...)` to `tests/functional/scenarios.py`:

   ```python
   Scenario(
       name="search_drawings",
       question="find drawings referencing ABC-123",
       expected_api_name="drawings",
       expected_api_request={"drawing_reference": "ABC-123", "include_relationships": True},
       mock_api_response={
           "matches": [
               {"drawing_reference": "ABC-123", "connected_assets": ["SIGNAL-7"]}
           ],
           "count": 1,
       },
       expected_answer_tokens=("ABC-123", "SIGNAL-7"),
       forbidden_answer_tokens=("password",),
   )
   ```

2. No other files need to change. The mock API takes any dict, the
   assertions check tokens, the harness doesn't care that `drawings`
   exists.

3. The Scenario owns its request shape, response shape, expected tokens,
   and forbidden tokens. Adding a new API is data, not code.

## Costs

| Command | AWS/LLM cost |
|---|---|
| `pytest` | None — runs mocks only |
| `pytest -m "functional and not deployed"` | None |
| `RUN_DEPLOYED_FUNCTIONAL_TESTS=true pytest -m deployed` | Lambda invocations + LLM tokens + API calls |

Deployed tests are explicitly opt-in via env vars. Default `pytest` is
free.

## Fictional vs real scenarios

Every scenario has `run_against_deployed_lambda: bool = False`. Fictional
examples MUST keep this `False`. Real business scenarios opt in
deliberately.

This guarantees the fictional examples can never accidentally run
against real infrastructure — they describe made-up APIs that don't exist
in production.