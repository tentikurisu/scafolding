"""Shared fixtures, helpers, and pytest hooks.

This conftest also emits a JSON summary report to `reports/run-<timestamp>.json`
after every `pytest` invocation. Tests can attach per-test extra data via the
`report_writer` fixture.

Scenario / API / N-run values are read from `repeatability.yaml` (or env
overrides). Python defaults apply if no config is loaded.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pytest

from repeatability_scaffold.config import (
    get_apis_config,
    get_config,
    get_scenarios_config,
    get_tests_config,
)


# === Configuration =================================================

def _resolve_n_runs() -> int:
    cfg_tests = get_tests_config()
    if "n_runs" in cfg_tests:
        return int(cfg_tests["n_runs"])
    return int(os.environ.get("N_RUNS", "10"))


def _resolve_jaccard_threshold() -> float:
    cfg_tests = get_tests_config()
    if "jaccard_threshold" in cfg_tests:
        return float(cfg_tests["jaccard_threshold"])
    return float(os.environ.get("JACCARD_THRESHOLD", "0.95"))


def _resolve_report_dir() -> str:
    cfg_tests = get_tests_config()
    if "report_dir" in cfg_tests:
        return str(cfg_tests["report_dir"])
    return os.environ.get("REPORT_DIR", "reports")


DEFAULT_N_RUNS = _resolve_n_runs()
JACCARD_THRESHOLD = _resolve_jaccard_threshold()
REPORT_DIR = _resolve_report_dir()


# === Scenario / behavior constants =================================
# These are populated from config (when present) or fall back to defaults.

_DEFAULT_SCENARIOS: list[str] = [
    "fetch_color_red",
    "fetch_color_xyz",
    "check_prime_17",
    "check_negative_number",
    "describe_pentagon",
    "describe_unknown_shape",
]


_DEFAULT_API_NAMES: list[str] = ["colors", "numbers", "shapes"]


def _scenarios_from_config() -> list[str]:
    cfg_scenarios = get_scenarios_config()
    if cfg_scenarios:
        return list(cfg_scenarios.keys())
    return list(_DEFAULT_SCENARIOS)


def _apis_from_config() -> list[str]:
    cfg_apis = get_apis_config()
    if cfg_apis:
        return list(cfg_apis.keys())
    return list(_DEFAULT_API_NAMES)


SCENARIOS: list[str] = _scenarios_from_config()
API_NAMES: list[str] = _apis_from_config()


# === Fixtures ======================================================

@pytest.fixture(scope="session")
def n_runs() -> int:
    return DEFAULT_N_RUNS


@pytest.fixture(scope="session")
def jaccard_threshold() -> float:
    return JACCARD_THRESHOLD


@pytest.fixture
def scenarios() -> list[str]:
    return list(SCENARIOS)


@pytest.fixture
def api_names() -> list[str]:
    return list(API_NAMES)


@pytest.fixture
def behaviors() -> list[str]:
    from repeatability_scaffold.behaviors.catalog import BEHAVIORS
    return list(BEHAVIORS)


@pytest.fixture
def llm_client():
    from repeatability_scaffold.pipeline.llm_client import LLMClient
    return LLMClient()


@pytest.fixture
def api_registry():
    from repeatability_scaffold.pipeline.api_registry import build_default_registry
    return build_default_registry()


@pytest.fixture
def execution_lambda(llm_client, api_registry):
    from repeatability_scaffold.pipeline.execution_lambda import ExecutionLambda
    return ExecutionLambda(llm_client, api_registry)


# === Run-N-times helpers ===========================================

def run_n_times_sync(fn: Callable[..., Any], *args: Any, n: int = DEFAULT_N_RUNS, **kwargs) -> list[Any]:
    """Run a sync callable N times. Used by tests that don't need async."""
    return [fn(*args, **kwargs) for _ in range(n)]


async def run_n_times_async(
    coro_factory: Callable[[], Any],
    n: int = DEFAULT_N_RUNS,
) -> list[Any]:
    """Run an async callable N times. `coro_factory` should be a no-arg callable returning a coroutine."""
    return [await coro_factory() for _ in range(n)]


@pytest.fixture
def run_n_sync():
    return run_n_times_sync


@pytest.fixture
def run_n_async():
    async def _runner(coro_factory, n: int = DEFAULT_N_RUNS):
        return await run_n_times_async(coro_factory, n=n)
    return _runner


# === JSON report writer ============================================

@dataclass
class TestRecord:
    nodeid: str
    outcome: str = "unknown"
    duration_s: float = 0.0
    extras: dict[str, Any] = field(default_factory=dict)


_RECORDS: list[TestRecord] = []
_EXTRAS_BY_NODEID: dict[str, list[dict[str, Any]]] = {}


@pytest.fixture
def report_writer(request):
    """Tests can call `report_writer(scenario=..., jaccard=..., ...)` to attach
    extra fields to the test's entry in the JSON report.
    """
    entries: list[dict[str, Any]] = []
    _EXTRAS_BY_NODEID[request.node.nodeid] = entries

    def _add(**kwargs: Any) -> None:
        entries.append(kwargs)

    yield _add


def pytest_runtest_logreport(report):
    if report.when != "call":
        return
    extras_list = _EXTRAS_BY_NODEID.get(report.nodeid, [])
    extras_dict: dict[str, Any] = {}
    for entry in extras_list:
        for k, v in entry.items():
            if k in extras_dict:
                if isinstance(extras_dict[k], list):
                    extras_dict[k].append(v)
                else:
                    extras_dict[k] = [extras_dict[k], v]
            else:
                extras_dict[k] = v
    _RECORDS.append({
        "nodeid": report.nodeid,
        "outcome": report.outcome,
        "duration_s": round(report.duration, 6),
        "extras": extras_dict,
    })


def pytest_sessionfinish(session, exitstatus):
    if not REPORT_DIR:
        return

    out_dir = Path(REPORT_DIR)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    total = len(_RECORDS)
    passed = sum(1 for r in _RECORDS if r["outcome"] == "passed")
    failed = sum(1 for r in _RECORDS if r["outcome"] == "failed")
    skipped = sum(1 for r in _RECORDS if r["outcome"] == "skipped")

    summary = {
        "run_id": timestamp,
        "exit_status": exitstatus,
        "n_runs_default": DEFAULT_N_RUNS,
        "jaccard_threshold": JACCARD_THRESHOLD,
        "totals": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": (passed / total) if total else 1.0,
        },
        "tests": _RECORDS,
    }

    out_path = out_dir / f"run-{timestamp}.json"
    out_path.write_text(json.dumps(summary, indent=2, default=str))


def pytest_collection_modifyitems(config, items):
    # Quiet hook placeholder; keeps import-time side effects minimal.
    pass