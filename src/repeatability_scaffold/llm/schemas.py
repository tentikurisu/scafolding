"""Pydantic schemas for LLM responses.

Forgiving by default: `extra="ignore"` so a stub (or real LLM) that adds extra
fields does not break validation. We use plain `str` (not Literal) for `action`
and `target_api` so that genuinely novel outputs do not raise ValidationError;
membership checks happen in the evaluator instead.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

VALID_ACTIONS = ("fetch", "describe", "check", "explain", "list", "compute")
VALID_TARGET_APIS = ("colors", "numbers", "shapes")


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action: str = ""
    target_api: str = ""
    params: dict[str, Any] = {}
    reasoning: str = ""

    def is_well_formed(self) -> bool:
        return (
            self.action in VALID_ACTIONS
            and self.target_api in VALID_TARGET_APIS
            and isinstance(self.params, dict)
        )