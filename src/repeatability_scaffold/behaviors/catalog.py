"""Catalog of placeholder API behaviors.

Nine behaviors per API:

  SUCCESS_SHAPED:
    - successful            : full valid response
    - empty                 : {} returned
    - not_found             : None returned (or 404)
    - missing_field         : partial response
    - malformed_payload     : response with wrong types/shapes

  ERROR_SHAPED (the API raises):
    - api_400               : BadRequestError
    - api_401_403           : AuthError
    - api_500               : ServerError
    - timeout               : TimeoutError_

Reads `behaviors:` from `repeatability.yaml` if present; otherwise uses the
Python defaults below.
"""

from __future__ import annotations

from ..config import get_behaviors_config


_DEFAULT_BEHAVIORS: list[str] = [
    "successful",
    "empty",
    "not_found",
    "missing_field",
    "malformed_payload",
    "api_400",
    "api_401_403",
    "api_500",
    "timeout",
]


_DEFAULT_SUCCESS_SHAPED: list[str] = [
    "successful",
    "empty",
    "not_found",
    "missing_field",
    "malformed_payload",
]


_DEFAULT_ERROR: list[str] = [
    "api_400",
    "api_401_403",
    "api_500",
    "timeout",
]


def _load_behaviors() -> tuple[list[str], list[str], list[str]]:
    """Return (all, success_shaped, error) lists, merging config + defaults."""
    all_cfg = get_behaviors_config()
    if all_cfg is None:
        return list(_DEFAULT_BEHAVIORS), list(_DEFAULT_SUCCESS_SHAPED), list(_DEFAULT_ERROR)

    all_b = list(all_cfg)
    success = [b for b in all_b if b not in _DEFAULT_ERROR]
    error = [b for b in all_b if b in _DEFAULT_ERROR]
    # If config didn't include the standard error names, fall back to defaults for error list
    if not error:
        error = [b for b in all_b if b in _DEFAULT_ERROR] or list(_DEFAULT_ERROR)
    return all_b, success, error


BEHAVIORS, SUCCESS_SHAPED_BEHAVIORS, ERROR_BEHAVIORS = _load_behaviors()


def reload_from_config() -> None:
    """Re-read behaviors from config. Modifies module globals."""
    global BEHAVIORS, SUCCESS_SHAPED_BEHAVIORS, ERROR_BEHAVIORS
    BEHAVIORS, SUCCESS_SHAPED_BEHAVIORS, ERROR_BEHAVIORS = _load_behaviors()