"""Pydantic models shared across the scaffold and tests.

Uses Field(default_factory=...) for all mutable defaults — no dict/list defaults.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExecutionResult(BaseModel):
    """Normalized result from any SystemUnderTest.invoke().

    Both LocalMockSystem and AwsLambdaSystem return this shape.
    """

    model_config = ConfigDict(extra="ignore")

    response_text: str = ""
    target_api: Optional[str] = None
    tool_parameters: dict[str, Any] = Field(default_factory=dict)
    api_response: Optional[dict | list] = None
    api_error: Optional[str] = None
    api_error_category: Optional[str] = None  # client_error / server_error / timeout / etc.
    raw_response: Optional[dict] = None  # full response from Lambda / mock (debug aid)


class Scenario(BaseModel):
    """One test scenario. Each (name, behavior) pair is one scenario instance.

    Tests consume SCENARIOS through pytest parametrize. Adding a real business
    scenario is a data change here, not an edit to multiple test files.
    """

    model_config = ConfigDict(extra="ignore")

    name: str
    prompt: str
    behavior: str = "successful"

    # Expected tool-call metadata (what the LLM should pick).
    # Skipped in real-target assertions if the Lambda doesn't expose this info.
    expected_target_api: Optional[str] = None
    expected_tool_parameters: dict[str, Any] = Field(default_factory=dict)

    # Expected agent_message content.
    expected_response_tokens: list[str] = Field(default_factory=list)
    forbidden_response_tokens: list[str] = Field(default_factory=list)

    # Expected API response shape (skipped if the Lambda doesn't expose it).
    expected_api_fields: dict[str, Any] = Field(default_factory=dict)

    # One of: "success", "client_error", "auth_error", "server_error", "timeout", "not_found", "empty".
    expected_error_category: Optional[str] = None

    # Repeatability tuning.
    minimum_pass_rate: float = 1.0
    run_count: int = 10

    # Set False to skip real-Lambda runs (e.g., fault-injection scenarios).
    supports_real_target: bool = True

    # Optional notes for debugging.
    notes: str = ""