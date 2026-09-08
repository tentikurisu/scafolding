"""Repeatability scaffold.

A small library for testing LLM -> execution lambda -> API repeatability.
Drop the `scaffold/` directory into your repo's tests folder.

Two system-under-test implementations:
  - LocalMockSystem : deterministic local mocks (default, no AWS)
  - AwsLambdaSystem  : real AWS Lambda invocation

Switch via the TEST_TARGET env var (mock | lambda). See README.md.
"""

from .config import Config, get_config, reset_config
from .models import ExecutionResult, Scenario
from .scenarios import ALL_SCENARIOS, scenarios_for_target, by_name
from .validators import (
    contains_all,
    contains_none,
    jaccard,
    fields_match,
    fields_match_report,
    validate_pydantic,
    category_for_error,
)
from .mock_llm import MockLLM, LLMResponse, validate_llm_response
from .mock_apis import (
    APIClient,
    MockColorsClient,
    MockNumbersClient,
    MockShapesClient,
    default_mock_apis,
    FaultInjector,
    SimulatedError,
    SimulatedBadRequest,
    SimulatedAuthError,
    SimulatedServerError,
    SimulatedTimeout,
)
from .models import ExecutionResult, Scenario
from .mock_system import LocalMockSystem
from .bedrock_llm import BedrockLLM
from .lambda_system import AwsLambdaSystem, LambdaInvocationError
from .api_adapter import (
    ApiAdapter,
    APIError,
    APIClientError,
    APIAuthError,
    APINotFoundError,
    APIServerError,
)
from .system import SystemUnderTest, make_system

__all__ = [
    # Config
    "Config", "get_config", "reset_config",
    # Models
    "ExecutionResult", "Scenario",
    # Scenarios
    "ALL_SCENARIOS", "scenarios_for_target", "by_name",
    # Validators
    "contains_all", "contains_none", "jaccard",
    "fields_match", "fields_match_report", "validate_pydantic", "category_for_error",
    # Mock LLM
    "MockLLM", "LLMResponse", "validate_llm_response",
    # Mock APIs
    "APIClient", "MockColorsClient", "MockNumbersClient", "MockShapesClient",
    "default_mock_apis", "FaultInjector",
    "SimulatedError", "SimulatedBadRequest", "SimulatedAuthError",
    "SimulatedServerError", "SimulatedTimeout",
    # Mock system
    "LocalMockSystem",
    # Real LLM
    "BedrockLLM",
    # Real Lambda
    "AwsLambdaSystem", "LambdaInvocationError",
    # HTTP API adapter
    "ApiAdapter", "APIError", "APIClientError", "APIAuthError",
    "APINotFoundError", "APIServerError",
    # System abstraction
    "SystemUnderTest", "make_system",
]