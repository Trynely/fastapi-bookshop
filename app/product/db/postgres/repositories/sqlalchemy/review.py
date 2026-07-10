import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from app.product.db.postgres.models.book import BookModel
from app.product.db.postgres.models.review import ReviewModel
from app.product.dto.review.filter_by_user_and_book import BookReviewOFUser
from app.shared.api.requests.offset_pagination import OffsetPagination
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO
from app.shared.dto.page_pagintaion import PagePaginationResult

class BookReviewSQLAlchemyREPO(BaseSQLAlchemyREPO[ReviewModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=ReviewModel,
        )

    async def get_list_by_book_slug(
        self,
        book_slug: str,
        pagination: OffsetPagination,
    ) -> PagePaginationResult:
        count_stmt = (
            select(func.count(self.model.id))
            .join(BookModel, self.model.book_id == BookModel.id)
            .where(BookModel.slug == book_slug)
        )
        total: int = await self.session.scalar(count_stmt) or 0

        stmt = (
            select(self.model)
            .join(BookModel, self.model.book_id == BookModel.id)
            .options(joinedload(self.model.user))
            .where(BookModel.slug == book_slug)
            .limit(pagination.limit)
            .offset(pagination.offset)
        )

        result = await self.session.execute(stmt)
        items = result.scalars().all()

        pages = math.ceil(total / pagination.limit) if total > 0 else 1

        return PagePaginationResult(
            items=items,
            page=pagination.page,
            page_size=pagination.limit,
            total=total,
            pages=pages,
        )

    async def get_list_by_book_id(self, book_id: int) -> list[ReviewModel]:
        stmt = (
            select(self.model)
            .join(BookModel, self.model.book_id == BookModel.id)
            .where(BookModel.id == book_id)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_book_and_user_id(self, filters: BookReviewOFUser) -> ReviewModel | None:
        stmt = select(self.model).where(
            self.model.book_id == filters.book_id,
            self.model.user_id == filters.user_id,
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()