from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.product.db.postgres.models.author import AuthorModel
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO

class BookAuthorSQLAlchemyREPO(BaseSQLAlchemyREPO[AuthorModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=AuthorModel,
        )
    
    async def get_by_ids(self, author_ids: list[int]) -> list[AuthorModel]:
        authors = await self.session.execute(
            select(self.model).where(
                self.model.id.in_(author_ids)
            )
        )
        return authors.scalars().all()