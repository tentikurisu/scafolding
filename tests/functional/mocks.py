"""Configurable mock API. One generic class for any API.

The mock API's production-facing method shape is `async def call(request)`.
That may differ from your real client's signature; map the difference in
`install_test_dependencies()` or in `test_local_handler.py` if needed.

Configure per scenario:
    mock = ConfigurableMockAPI(
        response=scenario.mock_api_response,
        expected_request=scenario.expected_api_request,
        exception=scenario.mock_api_exception,
    )
"""

from __future__ import annotations

from typing import Any, Optional


class ConfigurableMockAPI:
    """Records calls, asserts expected request, returns/raises configured value."""

    def __init__(
        self,
        response: Any = None,
        expected_request: Any = None,
        exception: Optional[BaseException] = None,
    ) -> None:
        self.response = response
        self.expected_request = expected_request
        self.exception = exception
        self.calls: list = []

    async def call(self, request) -> Any:
        self.calls.append(request)
        if self.expected_request is not None:
            assert request == self.expected_request, (
                f"Mock API received unexpected request.\n"
                f"  expected: {self.expected_request!r}\n"
                f"  received: {request!r}"
            )
        if self.exception is not None:
            raise self.exception
        return self.response

    def assert_called_with(self, expected_request: Any) -> None:
        """Convenience for tests that don't use the constructor-time assertion."""
        assert self.calls, "Mock API was never called"
        assert self.calls[-1] == expected_request, (
            f"Last call did not match.\n  expected: {expected_request!r}\n  got: {self.calls[-1]!r}"
        )