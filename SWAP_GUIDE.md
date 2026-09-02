# Swap Guide — Bedrock LLM + Your APIs + Test Tokens

The scaffold ships with **mocks** (no network, no AWS creds needed):
- `MockLLM` — deterministic LLM stub
- `MockColorsAPI`, `MockNumbersAPI`, `MockShapesAPI` — minimal API stubs

You'll swap these for **real** implementations. Most users only need to change **2 lines** in `conftest.py`.

---

## TL;DR — switch to Bedrock

1. `pip install aioboto3`
2. Set AWS env vars (or use IAM role / `~/.aws/credentials`)
3. Edit `conftest.py`: change **one line**:
   ```python
   llm_factory = MockLLM          # ← change to:
   llm_factory = BedrockLLM       # ← BedrockLLM
   ```
4. `pytest: `

That's it. Tests run unchanged against Bedrock.

---

## 1. Real LLM (AWS Bedrock)

### The interface (mock and real both implement this)

```python
class YourLLM:
    async def first_call(self, prompt: str, scenario: str) -> dict:
        """Return the LLM's decision: {"action", "target_api", "params", "reasoning"}."""

    async def second_call(
        self,
        scenario: str,
        behavior: str,
        api_response: dict | None,
        api_error: str | None,
    ) -> str:
        """Return the user-facing agent message."""
```

### `BedrockLLM` (working implementation, ready to use)

**File**: `bedrock_llm.py`

```python
from bedrock_llm import BedrockLLM

# Reads env vars: AWS_REGION, BEDROCK_MODEL_ID, BEDROCK_TEMPERATURE
llm = BedrockLLM()

# Or explicit config:
llm = BedrockLLM(
    model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region="us-east-1",
    temperature=0.0,
)
```

**Install**:
```bash
pip install aioboto3
```

**AWS auth** — any method supported by boto3 works:
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` env vars
- `~/.aws/credentials` file
- IAM role (on EC2/ECS/Lambda)

### How the Bedrock implementation works

`BedrockLLM` uses Bedrock's **Converse API** with **tool use** to force structured output:

- **First call** (`first_call`): user prompt → tool call → `{"action", "target_api", "params", "reasoning"}`
- **Second call** (`second_call`): API response + behavior → tool call → user message string

Temperature defaults to **0.0** for maximum determinism.

### Where to plug it in (1 line)

In **`conftest.py`**, find the SWAP block:

```python
# SWAP: choose LLM (mock or real Bedrock)
llm_factory = MockLLM          # ← MOCKS (default). Change to: BedrockLLM
```

Change to:

```python
llm_factory = BedrockLLM       # ← real Bedrock
```

Done. Run `pytest` and you're testing against Bedrock.

---

## 2. Real APIs

### The interface (mock and real both implement this)

```python
class YourAPI:
    name: str  # must match the LLM's target_api

    async def call(self, params: dict, behavior: str) -> dict | None:
        """Return response dict, None for not_found, or raise for errors."""
```

### 9 behaviors

Your real API doesn't need to fake all 9 — only the ones your system naturally produces:

| `behavior` | What your `call` does |
|---|---|
| `"successful"` | Real lookup, return data dict |
| `"empty"` | Return `{}` |
| `"not_found"` | Return `None` |
| `"missing_field"` | Return partial data |
| `"malformed_payload"` | Return wrong types (test only) |
| `"api_400" / "api_401_403" / "api_500" / "timeout"` | Raise an exception |

### Examples

See `real_examples.py` for working patterns:

- `PostgresColorsAPI` / `PostgresNumbersAPI` — asyncpg
- `HttpColorsAPI` — httpx

### Where to plug it in

**Edit `pipeline.py`**:

```python
# BEFORE:
def default_mock_apis() -> dict:
    return {
        "colors": MockColorsAPI(),
        "numbers": MockNumbersAPI(),
        "shapes": MockShapesAPI(),
    }

# AFTER:
from myapp.clients import PostgresColorsAPI, PostgresNumbersAPI

def default_mock_apis() -> dict:
    pool = my_db_pool  # your asyncpg pool
    return {
        "colors": PostgresColorsAPI(pool),
        "numbers": PostgresNumbersAPI(pool),
    }
```

Then in **`conftest.py`**:

```python
llm_factory = BedrockLLM                                    # real LLM
apis_factory = default_mock_apis                            # real APIs (via your pipeline.py edit)
```

---

## 3. Test Tokens

Tokens are the words/phrases your `agent_message` **must contain** for each (scenario, behavior) combo.

### Where they live

In **`conftest.py`**:

```python
EXPECTED_TOKENS: dict[tuple[str, str], list[str]] = {
    ("fetch_red", "successful"):       ["red", "#FF0000"],
    ("fetch_red", "empty"):            ["unavailable"],
    ("fetch_red", "not_found"):        ["not found"],
    # ...
}
```

- **Key**: `(scenario_name, behavior_name)`
- **Value**: list of strings that must ALL appear (case-insensitive substring) in `agent_message`

### Add a new scenario (3-step recipe)

**1. Add the LLM decision + agent message in `llm.py`:**
```python
STUB_RESPONSES["fetch_blue"] = {
    "action": "fetch", "target_api": "colors",
    "params": {"name": "blue"},
    "reasoning": "Looking up blue.",
}
AGENT_MESSAGES[("fetch_blue", "successful")] = "Blue has hex #0000FF."
```

**2. Add the scenario name to `SCENARIOS` in `conftest.py`:**
```python
SCENARIOS = ["fetch_red", "check_17", "describe_pentagon", "fetch_blue"]
```

**3. Add expected tokens in `EXPECTED_TOKENS`:**
```python
EXPECTED_TOKENS.update({
    ("fetch_blue", "successful"):       ["blue", "#0000FF"],
    ("fetch_blue", "empty"):            ["unavailable"],
    # ... one per behavior
})
```

### What tokens to use

| Behavior | Good tokens |
|---|---|
| `successful` | Real values from API (`["red", "#FF0000"]`) — proves agent *used* the data |
| `empty` | `["unavailable"]` |
| `not_found` | `["not found"]` |
| `missing_field` | Available field + `["partial", "missing"]` |
| `malformed_payload` | `["unexpected"]` or `["parsed"]` |
| `api_400` | `["invalid"]` |
| `api_401_403` | `["access", "authorized"]` |
| `api_500` | `["error", "service"]` |
| `timeout` | `["unavailable", "timed out"]` |

### Verify tokens match your agent messages

Case-insensitive substring:
- ✓ `"Red has hex #FF0000"` contains `["red", "#FF0000"]`
- ✓ `"Color not found"` contains `["not found"]`
- ✗ `"No record found"` does **not** contain `["not found"]` (reversed order)

---

## Mock vs Real

| Term | Meaning | In scaffold? |
|---|---|---|
| **Mock** | Deterministic stub, no network | ✓ `MockLLM`, `MockColorsAPI`, etc. |
| **Real** | Your production impl (Bedrock, Postgres, HTTP) | ✗ You provide |

The scaffold never calls mocks "real" or your impls "mocks". Tests don't know which they're running — they only see the LLM and APIClient interfaces.

---

## Quick reference

| What | Where |
|---|---|
| **Swap to real LLM** | `conftest.py`: `llm_factory = BedrockLLM` (1 line) |
| **Swap to real APIs** | `pipeline.py` (`default_mock_apis`) — your factory |
| **Add scenario** | `llm.py` + `conftest.py` (`SCENARIOS`, `EXPECTED_TOKENS`) |
| **Change expected tokens** | `conftest.py` (`EXPECTED_TOKENS`) |
| **Change behaviors tested** | `conftest.py` (`BEHAVIORS`) + `test_behavior.py` (parametrize rows) |

**Zero changes to `test_*.py` files. Ever.**