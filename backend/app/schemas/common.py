"""Standard response envelope and pagination helpers.

Every successful API response is wrapped so the mobile client sees one shape:
    {"success": true, "data": ..., "error": null, "meta": ...}
Errors (handled centrally) use the same shape with success=false.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: object | None = None


class Envelope(BaseModel, Generic[T]):
    success: bool = True
    data: T | None = None
    error: ErrorDetail | None = None
    meta: PageMeta | None = None


def ok(data: T, *, meta: PageMeta | None = None) -> Envelope[T]:
    return Envelope[T](success=True, data=data, error=None, meta=meta)


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def to_meta(self, total: int) -> PageMeta:
        total_pages = (total + self.page_size - 1) // self.page_size if self.page_size else 0
        return PageMeta(
            total=total,
            page=self.page,
            page_size=self.page_size,
            total_pages=total_pages,
        )
