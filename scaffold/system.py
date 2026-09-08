"""SystemUnderTest protocol + factory.

Two implementations:
  - LocalMockSystem : runs the mocked LLM/API orchestration locally.
  - AwsLambdaSystem  : invokes a real AWS Lambda and normalizes the result.

Switch via TEST_TARGET env var. Tests never need to change.
"""

from __future__ import annotations

from typing import Protocol

from .config import Config
from .models import ExecutionResult


class SystemUnderTest(Protocol):
    """Abstraction shared by local mocked testing and real Lambda testing."""

    async def invoke(
        self,
        prompt: str,
        scenario: str | None = None,
        behavior: str = "successful",
    ) -> ExecutionResult: ...


def make_system(config: Config | None = None) -> SystemUnderTest:
    """Build the SystemUnderTest based on TEST_TARGET.

    - TEST_TARGET=mock     (default) -> LocalMockSystem
    - TEST_TARGET=lambda            -> AwsLambdaSystem
    """
    from .mock_system import LocalMockSystem
    from .lambda_system import AwsLambdaSystem

    cfg = config or Config.from_env()
    if cfg.test_target == "lambda":
        return AwsLambdaSystem(cfg)
    if cfg.test_target == "mock":
        return LocalMockSystem()
    raise ValueError(
        f"Unknown TEST_TARGET={cfg.test_target!r}. Use 'mock' or 'lambda'."
    )