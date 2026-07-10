from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.product.db.postgres.models.author import AuthorModel
from app.product.db.postgres.models.book import BookModel
from app.product.db.postgres.models.category import BookCategoryModel


class AgentBooksSQLAlchemyREPO:
    """Read-only book queries used by the AI agent (exact filters branch)."""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _base_query(self):
        return (
            select(BookModel)
            .options(
                joinedload(BookModel.author),
                joinedload(BookModel.category),
            )
            .where(BookModel.is_available.is_(True))
        )

    async def get_by_ids(self, book_ids: list[int]) -> list[BookModel]:
        if not book_ids:
            return []

        stmt = self._base_query().where(BookModel.id.in_(book_ids))
        result = await self._session.execute(stmt)
        books = result.scalars().all()

        # keep the ranking produced by vector search
        order = {book_id: idx for idx, book_id in enumerate(book_ids)}
        return sorted(books, key=lambda b: order.get(b.id, len(order)))

    async def search_by_filters(
        self,
        title: Optional[str] = None,
        author_name: Optional[str] = None,
        category_name: Optional[str] = None,
        price_min: Optional[Decimal] = None,
        price_max: Optional[Decimal] = None,
        rating_min: Optional[Decimal] = None,
        limit: int = 10,
    ) -> list[BookModel]:
        stmt = self._base_query()

        if title:
            stmt = stmt.where(BookModel.title.ilike(f"%{title}%"))

        if author_name:
            stmt = stmt.join(
                AuthorModel,
                BookModel.author_id == AuthorModel.id,
            ).where(AuthorModel.name.ilike(f"%{author_name}%"))

        if category_name:
            stmt = stmt.join(
                BookCategoryModel,
                BookModel.category_id == BookCategoryModel.id,
            ).where(
                BookCategoryModel.title.ilike(f"%{category_name}%")
                | BookCategoryModel.slug.ilike(f"%{category_name}%")
            )

        if price_min is not None:
            stmt = stmt.where(BookModel.price >= price_min)

        if price_max is not None:
            stmt = stmt.where(BookModel.price <= price_max)

        if rating_min is not None:
            stmt = stmt.where(BookModel.rating >= rating_min)

        stmt = stmt.order_by(
            BookModel.rating.desc(),
            BookModel.total_sales.desc(),
        ).limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())
