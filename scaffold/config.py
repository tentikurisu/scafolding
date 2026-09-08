"""Environment-driven configuration for the repeatability scaffold.

Reads from environment variables; no secrets read from source-controlled files.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """All configuration in one place. Read from env at startup."""

    # Which system-under-test to use
    test_target: str = "mock"           # TEST_TARGET: "mock" | "lambda"

    # AWS / Lambda config (only used when test_target == "lambda")
    aws_region: str = "us-east-1"      # AWS_REGION
    lambda_name: str = ""              # EXECUTION_LAMBDA_NAME
    lambda_alias: str = ""             # EXECUTION_LAMBDA_ALIAS

    # Repeatability / pass-rate thresholds for functional tests
    run_count: int = 10                # FUNCTIONAL_RUN_COUNT
    min_pass_rate: float = 0.9         # FUNCTIONAL_MINIMUM_PASS_RATE

    # Optional HTTP API adapter for independent API contract tests
    api_base_url: str = ""             # API_BASE_URL
    api_auth_header: str = ""          # API_AUTH_HEADER (placeholder name only)

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            test_target=os.environ.get("TEST_TARGET", "mock").lower(),
            aws_region=os.environ.get("AWS_REGION", "us-east-1"),
            lambda_name=os.environ.get("EXECUTION_LAMBDA_NAME", ""),
            lambda_alias=os.environ.get("EXECUTION_LAMBDA_ALIAS", ""),
            run_count=int(os.environ.get("FUNCTIONAL_RUN_COUNT", "10")),
            min_pass_rate=float(os.environ.get("FUNCTIONAL_MINIMUM_PASS_RATE", "0.9")),
            api_base_url=os.environ.get("API_BASE_URL", ""),
            api_auth_header=os.environ.get("API_AUTH_HEADER", ""),
        )

    def require_lambda_config(self) -> None:
        """Raise a clear error if Lambda config is missing when needed."""
        if not self.lambda_name:
            raise RuntimeError(
                "TEST_TARGET=lambda but EXECUTION_LAMBDA_NAME is not set. "
                "Set EXECUTION_LAMBDA_NAME in your environment or .env."
            )


_config: Config | None = None


def get_config(refresh: bool = False) -> Config:
    """Get the cached config. Pass refresh=True to re-read env."""
    global _config
    if _config is None or refresh:
        _config = Config.from_env()
    return _config


def reset_config() -> None:
    """Clear cached config (useful in tests)."""
    global _config
    _config = None