from __future__ import annotations

import math
from typing import Any, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams:
    def __init__(
        self,
        offset: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    ):
        self.offset = offset
        self.limit = limit


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    offset: int
    limit: int
    has_next: bool
    has_prev: bool
    pages: int

    model_config = {"from_attributes": True}

    @classmethod
    def create(cls, items: list[T], total: int, offset: int, limit: int) -> "PaginatedResponse[T]":
        pages = math.ceil(total / limit) if limit > 0 else 0
        return cls(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
            has_next=offset + limit < total,
            has_prev=offset > 0,
            pages=pages,
        )
