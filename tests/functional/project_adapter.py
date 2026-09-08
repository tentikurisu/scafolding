"""Project-specific adapter.

This is the ONLY file that normally needs structural editing after the
harness is copied into the destination repository.

It exposes:

  ExecutionResult                 — normalized result shape tests assert against
  load_production_handler()       — returns the real Lambda handler
  build_lambda_event(scenario)    — translate scenario -> Lambda event
  normalize_response(raw)         — translate response -> ExecutionResult
  install_test_dependencies(...)  — patch prod LLM/API factories
  invoke_handler(handler, ev, cx) — call a handler whether sync or async

The placeholder implementation below is a literal example (clearly marked
with TODO). It demonstrates the expected interface but does NOT implement
production logic. When you copy this into your real repository:

  1. Replace _placeholder_handler with a direct import of your handler,
     OR set EXECUTION_HANDLER_PATH=module.path:function_name.
  2. Replace create_llm / create_api_registry with imports of your
     production factories (or remove them if your handler takes deps
     differently).
  3. Replace _placeholder_execute with the real execute() function, or
     delete it if your handler is self-contained.
  4. Update build_lambda_event and normalize_response to match your
     Lambda's actual event and response shapes.

The harness's tests do not need to change for any of the above.
"""

from __future__ import annotations

import importlib
import inspect
import os
from dataclasses import dataclass
from typing import Any, Awaitable, Optional


# === ExecutionResult: the normalized result shape ====================

@dataclass
class ExecutionResult:
    """What tests assert against. All fields optional; missing = skipped."""

    answer_text: str = ""
    target_api: Optional[str] = None
    tool_parameters: Optional[dict] = None
    api_response: Any = None
    api_error: Optional[str] = None
    api_error_category: Optional[str] = None
    raw_response: Any = None


# === Handler invocation (sync + async) ============================

async def invoke_handler(handler, event, context) -> Any:
    """Call a Lambda handler whether it's sync or async.

    AWS Lambda Python handlers are commonly synchronous but may be async.
    The local tests should not care which style the production code uses.
    """
    result = handler(event, context)
    if inspect.isawaitable(result):
        return await result
    return result


# === Production handler loading ====================================

def load_production_handler():
    """Return the production Lambda handler.

    Resolution order:
      1. EXECUTION_HANDLER_PATH env var (e.g. "my_project.execution:lambda_handler")
      2. The placeholder handler below (replace after copying into your repo)

    TODO: After copying this into your repo, prefer a direct import:
        from my_project.execution import lambda_handler
        return lambda_handler
    """
    path = os.environ.get("EXECUTION_HANDLER_PATH")
    if path:
        module_path, attr = path.split(":", 1)
        module = importlib.import_module(module_path)
        return getattr(module, attr)
    return _placeholder_handler


# === Placeholder handler ============================================
# This is a literal example. It uses create_llm / create_api_registry
# factories below so tests can patch them. Replace after copying.

async def _placeholder_handler(event, context):
    """PLACEHOLDER Lambda handler. Demonstrates the expected structure.

    TODO: Replace with a direct import of your real handler. Real
    handlers are often synchronous; this one is async for demo.
    """
    return await _placeholder_execute(
        event,
        llm=create_llm(),
        api_registry=create_api_registry(),
    )


async def _placeholder_execute(event, llm, api_registry):
    """PLACEHOLDER execute function. Minimal orchestration for the harness.

    The pattern is: get prompt -> ask LLM to pick API -> call API -> ask LLM
    to draft answer -> return dict. Your real execute may do more.

    TODO: Replace with your real execute() if your handler is not
    self-contained.
    """
    prompt = event.get("prompt", event.get("question", ""))

    decision = await llm.first_call(prompt, "default")
    target_api = (decision or {}).get("target_api", "") or (decision or {}).get("tool", "")
    params = (decision or {}).get("parameters", {}) or (decision or {}).get("arguments", {})

    api_response: Any = None
    api_error_name: Optional[str] = None
    api_error_category: Optional[str] = None
    if target_api and target_api in api_registry:
        try:
            api_response = await api_registry[target_api].call(params)
        except Exception as exc:
            # Use Exception (not BaseException) so control exceptions like
            # KeyboardInterrupt / SystemExit propagate normally.
            api_error_name = type(exc).__name__
            api_error_category = _categorize(exc)

    answer = await llm.second_call("default", "successful", api_response, api_error_name)

    return {
        "response_text": answer,
        "target_api": target_api or None,
        "tool_parameters": params,
        "api_response": api_response,
        "api_error": api_error_name,
        "api_error_category": api_error_category,
    }


def _categorize(exc: Exception) -> str:
    """Map an exception to a coarse error category."""
    name = type(exc).__name__.lower()
    if "timeout" in name:
        return "timeout"
    if "permission" in name or "auth" in name:
        return "auth_error"
    if "value" in name or "type" in name:
        return "client_error"
    return "server_error"


# === Factories (the DI points install_test_dependencies patches) ======

def create_llm():
    """Factory for the production LLM. Tests patch this to return mocks.

    TODO: Replace with your production factory. For example:
        from my_project.llm import build_default_llm
        return build_default_llm()
    """
    raise RuntimeError(
        "Placeholder create_llm() called. Production code should provide "
        "this; tests inject mocks via install_test_dependencies()."
    )


def create_api_registry():
    """Factory for the production API registry. Tests patch this too.

    TODO: Replace with your production factory. For example:
        from my_project.clients import build_default_registry
        return build_default_registry()
    """
    raise RuntimeError(
        "Placeholder create_api_registry() called. Production code should "
        "provide this; tests inject mocks via install_test_dependencies()."
    )


# === Adapter functions (the four to adapt after copying) ==========

def build_lambda_event(scenario) -> dict:
    """Translate a scenario into the Lambda event shape.

    TODO: Replace with your real event format. For example:
        return {"prompt": scenario.question, "user_id": "test-user"}
    """
    return {"prompt": scenario.question}


def normalize_response(raw: Any) -> ExecutionResult:
    """Translate the production Lambda response into ExecutionResult.

    TODO: Replace with your real response mapping. For example:
        return ExecutionResult(
            answer_text=raw["answer"],
            target_api=raw.get("trace", {}).get("tool"),
            tool_parameters=raw.get("trace", {}).get("arguments"),
            api_response=raw.get("trace", {}).get("api_response"),
            api_error=raw.get("error"),
            raw_response=raw,
        )
    """
    if not isinstance(raw, dict):
        return ExecutionResult(answer_text=str(raw), raw_response=raw)
    return ExecutionResult(
        answer_text=raw.get("response_text", raw.get("answer", "")),
        target_api=raw.get("target_api"),
        tool_parameters=raw.get("tool_parameters"),
        api_response=raw.get("api_response"),
        api_error=raw.get("api_error"),
        api_error_category=raw.get("api_error_category"),
        raw_response=raw,
    )


def install_test_dependencies(monkeypatch, mocks: dict) -> None:
    """Replace production LLM/API factories with test doubles.

    `mocks` is a dict built by the test, e.g.:
        {
            "llm": stub_llm,              # has .first_call, .second_call
            "registry": {"records": mock_api, ...},  # keyed by API name
        }

    TODO: Adapt to your production DI pattern. Examples:

    Module-level factories (common pattern):
        monkeypatch.setattr("my_project.execution.create_llm",
                            lambda: mocks["llm"])
        monkeypatch.setattr("my_project.execution.create_api_registry",
                            lambda: mocks["registry"])

    Class-based handler:
        # Patch the class methods your handler calls.
        monkeypatch.setattr(MyHandler, "create_llm", classmethod(lambda cls: mocks["llm"]))

    The placeholder below patches the in-module factories for the harness
    itself to work standalone.
    """
    import tests.functional.project_adapter as _self
    monkeypatch.setattr(_self, "create_llm", lambda: mocks["llm"])
    monkeypatch.setattr(_self, "create_api_registry", lambda: mocks["registry"])