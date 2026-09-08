"""Pytest fixtures and marker configuration.

An ordinary `pytest` run never contacts AWS. Deployed-marked tests are
skipped unless `RUN_DEPLOYED_FUNCTIONAL_TESTS=true` is set.
"""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip `deployed`-marked tests unless explicitly opted in."""
    if os.environ.get("RUN_DEPLOYED_FUNCTIONAL_TESTS", "").lower() != "true":
        skip_deployed = pytest.mark.skip(
            reason="Deployed Lambda tests require RUN_DEPLOYED_FUNCTIONAL_TESTS=true"
        )
        for item in items:
            if "deployed" in item.keywords:
                item.add_marker(skip_deployed)


@pytest.fixture
def fake_context():
    """Minimal AWS Lambda context substitute for local tests."""

    class _Context:
        function_name = "test-harness"
        aws_request_id = "test-request-id"
        invoked_function_arn = "arn:aws:lambda:test"

    return _Context()