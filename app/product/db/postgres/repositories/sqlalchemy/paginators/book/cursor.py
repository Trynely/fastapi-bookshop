import base64
from decimal import Decimal
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    Select,
    and_,
    or_,
    tuple_,
)
from typing import (
    Any,
    Optional,
    Sequence,
)
from app.product.db.postgres.models.book import BookModel
from app.shared.db.postgres.repositories.sqlalchemy.cursor_pagination import BaseSQLAlchemyCursorPaginator
from app.shared.dto.cursor_pagination import CursorPaginationDTO

class BookSQLAlchemyCursorPaginator(BaseSQLAlchemyCursorPaginator[BookModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=BookModel
        )

    async def paginate_by_score(
        self,
        stmt: Select,
        cursor: Optional[str],
        # score_column без дефолта: колонка score приходит из подзапроса
        # вызывающего кода (см. popularity_window_subquery), дефолт на модель
        # статистики молча собирал бы запрос без соответствующего join.
        score_column,
        id_column = BookModel.id,
    ) -> CursorPaginationDTO:
        if cursor:
            cursor_score, cursor_id = self._decode_cursor(cursor)
            # Используем явный OR вместо tuple_<:
            # tuple_ — PostgreSQL-специфика; явный вариант читаемее
            # и не зависит от диалекта.
            stmt = stmt.where(
                or_(
                    score_column < cursor_score,
                    and_(
                        score_column == cursor_score,
                        id_column    <  cursor_id,
                    ),
                )
            )

        stmt = stmt.limit(self.limit + 1)

        result = await self.session.execute(stmt)
        rows: Sequence[Any] = result.all()

        items  = [row[0] for row in rows[: self.limit]]
        scores = [row[1] for row in rows[: self.limit]]
        has_more = len(rows) > self.limit

        next_cursor = (
            self._encode_cursor(items[-1], scores[-1]) if has_more else None
        )

        return CursorPaginationDTO(
            items=items,
            next_cursor=next_cursor,
            has_more=has_more,
        )

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[Decimal, int]:
        """
        Декодирует курсор.
        Бросает ValueError при невалидном значении —
        обработчик выше должен вернуть HTTP 400.
        """
        try:
            decoded = json.loads(base64.b64decode(cursor).decode())
            score = Decimal(decoded["popularity_score"])  # не float — потери точности
            id_   = int(decoded["id"])
            return score, id_
        except (KeyError, ValueError,
                json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError(         # узкий except вместо голого Exception
                f"Invalid pagination cursor: {cursor!r}"
            ) from exc

    @staticmethod
    def _encode_cursor(book: BookModel, score: Any) -> str:
        payload = {
            "popularity_score": str(score or "0"),  # str, не float — точность сохраняется
            "id": book.id,
        }
        return base64.b64encode(json.dumps(payload).encode()).decode()
        
    async def paginate_new(
        self,
        stmt: Select,
        cursor: Optional[int],
    ) -> CursorPaginationDTO:
        if cursor:
            stmt = stmt.where(self.model.id < int(cursor))

        stmt = stmt.limit(self.limit + 1)
        result = await self.session.execute(stmt)
        items = result.scalars().all()

        has_more = len(items) > self.limit
        books = items[:self.limit]

        next_cursor = books[-1].id if has_more else None
    
        return CursorPaginationDTO(
            items=[book for book in books],
            next_cursor=next_cursor,
            has_more=has_more,
        )