"""Pydantic schemas for API responses.

All schemas use `extra="ignore"` so that stubbed (or real) APIs that return
extra fields don't break validation. Fields are optional where the source
data can be missing (`empty`, `missing_field` behaviors).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ColorsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    hex: str | None = None
    rgb: list[int] | None = None
    family: str | None = None
    complementary: str | None = None


class NumbersResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    n: int | None = None
    is_prime: bool | None = None
    is_square: bool | None = None
    parity: str | None = None
    factors: list[int] | None = None


class ShapesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    sides: int | None = None
    area_formula: str | None = None
    regular: bool | None = None


API_SCHEMAS: dict[str, type[BaseModel]] = {
    "colors": ColorsResponse,
    "numbers": NumbersResponse,
    "shapes": ShapesResponse,
}


def schema_for(api_name: str) -> type[BaseModel]:
    if api_name not in API_SCHEMAS:
        raise KeyError(f"Unknown API: {api_name!r}")
    return API_SCHEMAS[api_name]


def dump(value: Any) -> dict:
    """Dump a pydantic model or plain dict to a plain dict."""
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_none=False)
    return dict(value)