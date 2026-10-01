"""Pagination: query params (page, page_size) and the generic Page[T] response."""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


@dataclass(frozen=True)
class PageParams:
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def make_page(items: list[Any], total: int, params: PageParams) -> dict[str, Any]:
    pages = (total + params.page_size - 1) // params.page_size if total else 0
    return {"items": items, "total": total, "page": params.page, "page_size": params.page_size, "pages": pages}


async def paginate(
    session: AsyncSession, stmt: Select[Any], params: PageParams, *, scalars: bool = True
) -> tuple[list[Any], int]:
    """Run ``stmt`` with count + offset/limit. Returns (rows, total). Use ``make_page`` to build the response."""
    total = (await session.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))).scalar_one()
    result = await session.execute(stmt.offset(params.offset).limit(params.limit))
    rows = list(result.scalars().all()) if scalars else list(result.all())
    return rows, int(total)
