# Repeatability Scaffold

A compact scaffold for testing an **LLM → execution lambda → API** pipeline
twice: once against local mocks (fast, no AWS), once against a real AWS
Lambda (real LLM, real APIs).

The tests are written once and switch between targets via `TEST_TARGET`.

---

## What this gives you

| File | Role |
|---|---|
| `scaffold/` | The library — drop into your repo's `tests/` folder |
| `tests/unit/` | Pure unit tests (validators, models) |
| `tests/component/` | Mock LLM + mock APIs, no network |
| `tests/functional/` | Scenarios run against `SystemUnderTest` |
| `tests/integration/` | Real AWS Lambda (skipped without AWS) |
| `pyproject.toml` | Deps + pytest marker config |
| `.env.example` | Placeholder env vars (no real secrets) |

## How tests are organized

| Marker | Meaning | Touches network? |
|---|---|---|
| `unit` | Pure logic, no fixtures | No |
| `component` | Mock LLM + mock APIs | No |
| `functional` | End-to-end scenarios | No (mock) / Yes (lambda) |
| `integration` | Real Lambda | Yes |
| `mock_only` | Simulated fault injection | Skipped on lambda |
| `real` | Needs AWS creds | Skipped on mock |

Suggested invocations:

```bash
# Everything local, no AWS — what you run in CI
pytest -m "not real and not integration"

# Only the functional layer
pytest -m functional

# Same tests, against a real Lambda
TEST_TARGET=lambda EXECUTION_LAMBDA_NAME=my-lambda pytest -m "functional and not mock_only"
```

## The two system-under-test implementations

```python
class SystemUnderTest(Protocol):
    async def invoke(
        self,
        prompt: str,
        scenario: str | None = None,
        behavior: str = "successful",
    ) -> ExecutionResult: ...
```

- `LocalMockSystem` — runs LLM → API → LLM locally with mocks. Fast,
  deterministic, no AWS. Used by default and by CI.
- `AwsLambdaSystem` — invokes a real AWS Lambda via boto3 and normalizes
  the result into the same `ExecutionResult`.

Switch with `TEST_TARGET=mock|lambda`. Tests don't change.

## Running

### Local (default)

```bash
pip install -e ".[dev]"
pytest
```

Expected: `100 passed, 18 skipped`. Skipped tests are `integration` (need AWS).

### Against the real Lambda

```bash
export TEST_TARGET=lambda
export AWS_REGION=us-east-1
export EXECUTION_LAMBDA_NAME=my-execution-lambda
export AWS_ACCESS_KEY_ID=...          # or any other boto3 auth
export AWS_SECRET_ACCESS_KEY=...
pytest -m functional
```

Expected: functional tests run against the real Lambda; integration
tests need `pytest -m integration` explicitly (and AWS creds).

## Switching the LLM

The default `MockLLM` is deterministic. To swap in AWS Bedrock:

```python
# In a conftest or test file
from scaffold import LocalMockSystem
from scaffold.bedrock_llm import BedrockLLM

system = LocalMockSystem(llm=BedrockLLM(), api_registry=...)
```

Tests that rely on deterministic mock responses will need their thresholds
relaxed (the scaffold's `Scenario.minimum_pass_rate` defaults to 1.0;
set to 0.9 for real LLMs).

## Central scenario definitions

All test scenarios are defined once in `scaffold/scenarios.py`. Adding a
new scenario is one `Scenario(...)` object:

```python
Scenario(
    name="fetch_user_profile",
    prompt="look up user profile for alice",
    expected_target_api="users",
    expected_tool_parameters={"user_id": "alice"},
    expected_response_tokens=["alice", "profile"],
    forbidden_response_tokens=["password"],
    supports_real_target=True,
)
```

Tests parametrize over `scenarios_for_target(TEST_TARGET)`. Adding
`fetch_user_profile` to the central collection is the only change needed;
no edits across multiple test files.

## Fault injection (local mocks only)

The scaffold separates the production APIClient interface from fault
injection:

```python
# Production-shaped interface (no behavior arg):
class APIClient(Protocol):
    name: str
    async def call(self, params: dict) -> dict | list | None: ...

# Local-mock fault injection (test-only):
class FaultInjector:
    def __init__(self, client: APIClient): ...
    async def call(self, params, *, behavior="successful"): ...
```

Production code never sees a `behavior` argument. The `LocalMockSystem`
wraps each registered API in a `FaultInjector`. Tests targeting the real
Lambda don't run mock-only fault tests (`@pytest.mark.mock_only`,
auto-skipped).

## Real Lambda response mapping

`AwsLambdaSystem._parse_response` handles the two response shapes:

1. **Direct dict** (Lambda proxy integration):
   `{"response_text": "...", "target_api": "...", "api_error": "..."}`
2. **API Gateway style**: `{"statusCode": 200, "body": "<json>"}`

When you finalize the real Lambda's event/response schema, update this
one method — no test changes.

## HTTP API adapter

`scaffold/api_adapter.py` provides `ApiAdapter` for testing API endpoints
directly (not through the Lambda). Single entry point
`request_and_normalize` that handles auth, error mapping, and response
validation. Status codes preserved on exceptions. No committed
credentials; env-driven.

```python
adapter = ApiAdapter(
    base_url="https://api.internal/colors",
    default_headers={"Authorization": f"Bearer {os.environ['API_TOKEN']}"},
    schema=ColorsResponse,
)
result = await adapter.fetch_color("red")  # 404 -> None, 4xx -> APIClientError
```

## Why expectations come from contracts, not observed output

When integrating a real LLM, it is tempting to write expectations that
match whatever the LLM happens to produce. Don't. That codifies the
current model's behaviour into the tests and makes them pass even when
the model is wrong.

Instead:
- Express expectations as **requirements** ("the agent must say
  `not found` when the API returns nothing").
- Express **forbidden tokens** to catch hallucination ("the agent must
  not invent a hex code when the API returned nothing").
- Use `minimum_pass_rate` for real LLMs (e.g., 0.9) — accepts some
  drift but catches systematic failures.

## What may incur AWS costs

| Test | Cost |
|---|---|
| `unit/`, `component/`, `functional/` against mocks | None |
| `functional/` against `TEST_TARGET=lambda` | Lambda invocations + Bedrock tokens |
| `integration/test_lambda.py` | Same — Lambda invocations |
| HTTP API adapter tests (if you add them) | API endpoint requests |

Default `pytest` runs against mocks only. Real-AWS tests are explicitly
opt-in via `TEST_TARGET=lambda` or the `real` marker.

## Adding a new scenario

1. Add a `Scenario(...)` to `scaffold/scenarios.py`.
2. Set `supports_real_target` correctly:
   - `True` if safe to run against the real Lambda (no fault injection).
   - `False` for simulated 4xx/5xx/timeout — these are skipped on Lambda.
3. Provide stub decisions in `scaffold/mock_llm.py` (`STUB_RESPONSES`,
   `AGENT_MESSAGES`) so the local mock system has something to return.
4. Done. The functional and repeatability tests automatically parametrize
   over the new scenario.

## Adapting to your real Lambda

When the real Lambda's event/response contract is finalized:

1. Update `_build_event` in `scaffold/lambda_system.py` to match the
   expected event shape.
2. Update `_parse_response` to match the response shape (direct dict
   or API Gateway style).
3. No test changes needed.

## Files

```
scaffold/
├── __init__.py          re-exports
├── config.py            env-driven Config
├── models.py            ExecutionResult, Scenario (Pydantic)
├── scenarios.py         central scenario collection
├── validators.py        contains_all / jaccard / fields_match / category_for_error
├── api_schemas.py       response Pydantic models
├── api_adapter.py       HTTP API adapter (httpx)
├── mock_llm.py          MockLLM (deterministic)
├── mock_apis.py         Mock*API clients + FaultInjector
├── mock_system.py       LocalMockSystem (SystemUnderTest impl)
├── bedrock_llm.py       BedrockLLM (real, opt-in)
├── lambda_system.py     AwsLambdaSystem (real, opt-in)
└── system.py            SystemUnderTest protocol + factory

tests/
├── conftest.py          target selection + fixtures + markers
├── unit/
│   ├── test_validators.py
│   └── test_models.py
├── component/
│   ├── test_mock_behaviors.py
│   └── test_local_pipeline.py
├── functional/
│   ├── test_execution.py
│   └── test_repeatability.py
└── integration/
    └── test_lambda.py

pyproject.toml          deps + markers
.env.example            placeholder env vars
README.md               this file
```