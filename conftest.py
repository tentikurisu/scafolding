"""Pytest fixtures for the scaffold.

Edit SCENARIOS / BEHAVIORS / EXPECTED_TOKENS to match your domain.

TO SWITCH FROM MOCKS TO BEDROCK: change line marked SWAP below.
"""

from __future__ import annotations

import pytest

from llm import MockLLM
from pipeline import ExecutionLambda, default_mock_apis


# === SWAP TO BEDROCK =================================================
# By default: mocks (no AWS creds needed).
# For real Bedrock tests, change the SWAP line to use BedrockLLM:
#
#     from bedrock_llm import BedrockLLM
#     llm_factory = BedrockLLM
#
# BedrockLLM reads AWS_REGION / BEDROCK_MODEL_ID / BEDROCK_TEMPERATURE
# from env (or pass them to the constructor).
#
# Leave the apis_factory pointing at default_mock_apis() until you
# wire up your real DB-backed clients (see SWAP_GUIDE.md section 2).

# SWAP: choose LLM (mock or real Bedrock)
llm_factory = MockLLM          # ← MOCKS (default). Change to: BedrockLLM

# Leave this as-is until you have real DB-backed API clients
apis_factory = default_mock_apis


# === Configuration ===================================================

N_RUNS = 10

SCENARIOS = ["fetch_red", "check_17", "describe_pentagon"]

BEHAVIORS = [
    "successful", "empty", "not_found", "missing_field", "malformed_payload",
    "api_400", "api_401_403", "api_500", "timeout",
]


# Expected tokens in agent_message per (scenario, behavior).
# Edit these to change what your tests assert.
EXPECTED_TOKENS: dict[tuple[str, str], list[str]] = {
    ("fetch_red", "successful"):       ["red", "#FF0000"],
    ("fetch_red", "empty"):            ["unavailable"],
    ("fetch_red", "not_found"):        ["not found"],
    ("fetch_red", "missing_field"):    ["red"],
    ("fetch_red", "malformed_payload"): ["unexpected"],
    ("fetch_red", "api_400"):          ["invalid"],
    ("fetch_red", "api_401_403"):      ["access"],
    ("fetch_red", "api_500"):          ["error"],
    ("fetch_red", "timeout"):          ["unavailable"],

    ("check_17", "successful"):       ["prime", "17"],
    ("check_17", "empty"):            ["unavailable"],
    ("check_17", "not_found"):        ["not found"],
    ("check_17", "missing_field"):    ["17"],
    ("check_17", "malformed_payload"): ["unexpected"],
    ("check_17", "api_400"):          ["invalid"],
    ("check_17", "api_401_403"):      ["access"],
    ("check_17", "api_500"):          ["error"],
    ("check_17", "timeout"):          ["unavailable"],

    ("describe_pentagon", "successful"):       ["pentagon"],
    ("describe_pentagon", "empty"):            ["unavailable"],
    ("describe_pentagon", "not_found"):        ["not found"],
    ("describe_pentagon", "missing_field"):    ["pentagon"],
    ("describe_pentagon", "malformed_payload"): ["unexpected"],
    ("describe_pentagon", "api_400"):          ["invalid"],
    ("describe_pentagon", "api_401_403"):      ["access"],
    ("describe_pentagon", "api_500"):          ["error"],
    ("describe_pentagon", "timeout"):          ["unavailable"],
}


# === Fixtures ========================================================

@pytest.fixture
def n_runs():
    return N_RUNS


@pytest.fixture
def scenarios():
    return list(SCENARIOS)


@pytest.fixture
def behaviors():
    return list(BEHAVIORS)


@pytest.fixture
def llm():
    return llm_factory()


@pytest.fixture
def apis():
    return apis_factory()


@pytest.fixture
def execution_lambda(llm, apis):
    return ExecutionLambda(llm, apis)


@pytest.fixture
def expected_tokens():
    return dict(EXPECTED_TOKENS)