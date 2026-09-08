"""AwsLambdaSystem — invokes a real AWS Lambda via boto3.

This is the second SystemUnderTest implementation. Selected when
TEST_TARGET=lambda. Reads config from env, fails fast if Lambda config
is missing.

The Lambda owns the real API routing. This adapter does NOT simulate
API behaviors or reproduce Lambda internals — it just sends the prompt
and normalizes the response.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from .config import Config
from .models import ExecutionResult
from .validators import category_for_error


class LambdaInvocationError(Exception):
    """Raised when the Lambda call fails or returns an unparseable body."""
    def __init__(self, message: str, *, status_code: int | None = None,
                 function_error: str | None = None, raw: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.function_error = function_error
        self.raw = raw


def _build_event(prompt: str, scenario: str | None, behavior: str) -> dict:
    """Build the event payload sent to the Lambda.

    Centralised here so changing the Lambda's expected input shape is a
    one-line edit, not a search across test files.
    """
    return {
        "prompt": prompt,
        "scenario": scenario or "",
        "behavior": behavior,
    }


def _parse_response(raw_payload: Any) -> ExecutionResult:
    """Normalize the Lambda's response into an ExecutionResult.

    Handles two shapes:
      1. Direct dict (Lambda proxy integration):
         {"response_text": "...", "target_api": "...", "api_error": "..."}
      2. API Gateway style:
         {"statusCode": 200, "body": "<json string>"}

    Add new shapes here as your Lambda evolves. Tests never need to change.
    """
    if not isinstance(raw_payload, dict):
        raise LambdaInvocationError(
            f"Lambda returned non-dict payload: {type(raw_payload).__name__}",
            raw=raw_payload,
        )

    # API Gateway shape
    if "statusCode" in raw_payload and "body" in raw_payload:
        status = raw_payload.get("statusCode", 0)
        body = raw_payload.get("body", "")
        function_error = raw_payload.get("errorMessage")
        if status >= 400 or function_error:
            raise LambdaInvocationError(
                f"Lambda returned status={status}: {function_error or body}",
                status_code=status, function_error=function_error, raw=raw_payload,
            )
        try:
            parsed_body = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError as exc:
            raise LambdaInvocationError(
                f"Lambda body is not valid JSON: {exc}",
                status_code=status, raw=raw_payload,
            ) from exc
        if not isinstance(parsed_body, dict):
            raise LambdaInvocationError(
                f"Lambda body is not a dict: {type(parsed_body).__name__}",
                status_code=status, raw=raw_payload,
            )
        return ExecutionResult(**parsed_body)

    # Direct-dict shape
    return ExecutionResult(**raw_payload)


class AwsLambdaSystem:
    """Invokes a real AWS Lambda and normalizes the result.

    Requires:
        - boto3 (sync) or aioboto3 (async)
        - EXECUTION_LAMBDA_NAME env var (set when TEST_TARGET=lambda)
        - AWS credentials (any boto3-supported method)
    """

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.from_env()
        self.config.require_lambda_config()

    def _client(self):
        try:
            import boto3
        except ImportError as exc:
            raise ImportError(
                "AwsLambdaSystem requires boto3. Install with: pip install boto3"
            ) from exc
        return boto3.client("lambda", region_name=self.config.aws_region)

    async def invoke(
        self,
        prompt: str,
        scenario: str | None = None,
        behavior: str = "successful",
    ) -> ExecutionResult:
        """Invoke the Lambda asynchronously (boto3 sync client run in thread)."""
        event = _build_event(prompt, scenario, behavior)
        client = self._client()

        def _invoke():
            kwargs: dict[str, Any] = {
                "FunctionName": self.config.lambda_name,
                "InvocationType": "RequestResponse",
                "Payload": json.dumps(event).encode("utf-8"),
            }
            if self.config.lambda_alias:
                kwargs["Qualifier"] = self.config.lambda_alias
            return client.invoke(**kwargs)

        loop = asyncio.get_running_loop()
        try:
            resp = await loop.run_in_executor(None, _invoke)
        except Exception as exc:
            raise LambdaInvocationError(f"Lambda invocation failed: {exc}") from exc

        status_code = resp.get("StatusCode", 0)
        function_error = resp.get("FunctionError")
        payload_stream = resp.get("Payload")
        if payload_stream is None:
            raise LambdaInvocationError(
                "Lambda returned empty Payload",
                status_code=status_code, function_error=function_error, raw=None,
            )
        try:
            raw_text = payload_stream.read().decode("utf-8")
            raw_payload = json.loads(raw_text)
        except Exception as exc:
            raise LambdaInvocationError(
                f"Could not parse Lambda Payload: {exc}",
                status_code=status_code, function_error=function_error, raw=None,
            ) from exc

        result = _parse_response(raw_payload)
        # Tag the raw response for debugging.
        result.raw_response = raw_payload if isinstance(raw_payload, dict) else {"raw": raw_text}
        return result