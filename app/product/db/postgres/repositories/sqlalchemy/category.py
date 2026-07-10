from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.product.db.postgres.models.category import BookCategoryModel
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO


class BookCategorySQLAlchemyREPO(BaseSQLAlchemyREPO[BookCategoryModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=BookCategoryModel,
        )

    async def get_by_ids(self, category_ids: list[int]) -> list[BookCategoryModel]:
        if not category_ids:
            return []

        categories = await self.session.execute(
            select(self.model).where(
                self.model.id.in_(category_ids)
            )
        )
        return categories.scalars().all()