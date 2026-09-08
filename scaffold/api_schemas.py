"""Pydantic schemas for API responses.

Used by api_adapter and tests for validation. Real schemas will replace
these when integrating with production APIs.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ColorsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    hex: Optional[str] = None
    rgb: Optional[list[int]] = None
    family: Optional[str] = None
    complementary: Optional[str] = None


class NumbersResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    n: Optional[int] = None
    is_prime: Optional[bool] = None
    is_square: Optional[bool] = None
    parity: Optional[str] = None
    factors: Optional[list[int]] = None


class ShapesResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: Optional[str] = None
    sides: Optional[int] = None
    area_formula: Optional[str] = None
    regular: Optional[bool] = None