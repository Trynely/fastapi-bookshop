import hashlib
from sqlalchemy import (
    Select,
    func,
    literal,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeMeta
from app.core.config.base import get_settings
from app.shared.dto.cursor_pagination import CursorPaginationDTO
from typing import (
    Any,
    List,
    Sequence,
    Optional,
    Generic,
    TypeVar,
    Type,
)

settings = get_settings()

TModel = TypeVar("TModel", bound=DeclarativeMeta)

class BaseSQLAlchemyCursorPaginator(Generic[TModel]):
    def __init__(self, 
        session: AsyncSession,
        model: Type[TModel],
    ):
        self.session = session
        self.model = model
        
        self.limit = settings.db.limit
    
    async def paginate(
        self,
        stmt: Select,
        cursor: Optional[int],
    ) -> CursorPaginationDTO:
        stmt = stmt.order_by(self.model.id.asc())

        if cursor:
            stmt = stmt.where(self.model.id > cursor)

        stmt = stmt.limit(self.limit + 1)
        result = await self.session.execute(stmt)
        items: Sequence[Any] = result.scalars().all()

        has_more = len(items) > self.limit
        items = items[:self.limit]

        next_cursor = items[-1].id if has_more else None
        has_next = has_more

        if not has_next:
            next_cursor = None
    
        return CursorPaginationDTO(
            items=[item for item in items],
            next_cursor=next_cursor,
            has_more=has_next,
        )
    
    async def random_paginate(
        self,
        stmt: Select,
        seed: str,
        cursor: Optional[str],
    ) -> CursorPaginationDTO:
        random_expr = func.md5(func.concat(self.model.id, literal(seed)))
        stmt = stmt.order_by(random_expr.asc())

        if cursor:
            stmt = stmt.where(random_expr > literal(cursor))

        stmt = stmt.limit(self.limit + 1)
        result = await self.session.execute(stmt)
        items: Sequence[Any] = result.scalars().all()

        has_more = len(items) > self.limit
        items = items[:self.limit]

        def _hash_cursor(book_id: int, seed: str) -> str:
            return hashlib.md5(f"{book_id}{seed}".encode()).hexdigest()

        next_cursor = _hash_cursor(items[-1].id, seed) if has_more else None

        return CursorPaginationDTO(
            items=[item for item in items],
            next_cursor=next_cursor,
            has_more=has_more,
        )