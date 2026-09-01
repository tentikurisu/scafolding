"""Configuration loader.

The scaffold reads `repeatability.yaml` from the project root (or from the
path in `REPEATABILITY_CONFIG` env var) and exposes it as a dict. Every
module that has configurable behavior reads from this config, so users can:

- Switch LLM providers (stub <-> bedrock)
- Switch API clients (stub <-> HTTP)
- Add/remove scenarios
- Change what each test sends (prompts, params)
- Change what each test expects (token lists)

If no config file is present, the Python defaults are used unchanged.

Usage:

    from repeatability_scaffold.config import get_config, reload_config

    cfg = get_config()
    print(cfg["llm"]["provider"])
    reload_config()  # re-read from disk
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_NAME = "repeatability.yaml"


def _find_config_path(explicit: str | None = None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None

    env = os.environ.get("REPEATABILITY_CONFIG")
    if env:
        p = Path(env)
        if p.exists():
            return p

    candidates = [
        Path.cwd() / DEFAULT_CONFIG_NAME,
        Path(__file__).resolve().parents[2] / DEFAULT_CONFIG_NAME,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load config from YAML. Returns empty dict if no file found."""
    config_path = _find_config_path(path)
    if config_path is None:
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a mapping, got {type(data).__name__}")
    return data


_cached: dict[str, Any] | None = None
_cached_path: Path | None = None


def get_config(refresh: bool = False) -> dict[str, Any]:
    """Get the loaded config. Cached after first read.

    Pass `refresh=True` to force a re-read from disk (useful in tests after
    editing the YAML).
    """
    global _cached, _cached_path
    if refresh or _cached is None:
        _cached = load_config()
        _cached_path = _find_config_path()
    return _cached


def config_path() -> Path | None:
    """Return the path the config was loaded from, or None if no file."""
    if _cached_path is None:
        get_config()
    return _cached_path


def reload_config() -> dict[str, Any]:
    """Force re-read of config from disk."""
    return get_config(refresh=True)


def has_config() -> bool:
    """True iff a config file was found and loaded."""
    return config_path() is not None


# === Convenience accessors ==========================================

def get_llm_config() -> dict[str, Any]:
    return dict(get_config().get("llm", {}))


def get_apis_config() -> dict[str, Any]:
    return dict(get_config().get("apis", {}))


def get_scenarios_config() -> dict[str, Any]:
    return dict(get_config().get("scenarios", {}))


def get_behaviors_config() -> list[str] | None:
    """Returns the configured behaviors list, or None to use Python default."""
    cfg = get_config().get("behaviors")
    return list(cfg) if cfg else None


def get_tests_config() -> dict[str, Any]:
    return dict(get_config().get("tests", {}))