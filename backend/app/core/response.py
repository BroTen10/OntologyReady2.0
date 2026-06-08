from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PageInfo(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0


class PagedData(BaseModel, Generic[T]):
    items: list[T] = []
    page_info: PageInfo = Field(default_factory=PageInfo)


def ok(data: Any = None, message: str = "ok") -> dict:
    return ApiResponse(code=0, message=message, data=data).model_dump(mode="json")


def error(code: int, message: str, data: Any = None) -> dict:
    return ApiResponse(code=code, message=message, data=data).model_dump(mode="json")


def paged(items: list, total: int, page: int, page_size: int) -> dict:
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    page_info = PageInfo(page=page, page_size=page_size, total=total, total_pages=total_pages)
    return ok(PagedData(items=items, page_info=page_info))
