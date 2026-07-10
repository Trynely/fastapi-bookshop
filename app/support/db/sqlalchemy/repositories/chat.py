from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO
from app.support.models import ChatModel

class ChatSQLAlchemyRepository(BaseSQLAlchemyREPO[ChatModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=ChatModel,
        )

    async def get_by_user_id(self, user_id: int) -> Optional[ChatModel]:
        stmt = select(self.model).where(
            self.model.user_id == user_id,
            self.model.is_closed.is_(False),
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_is_not_closed(self, chat_id: int) -> Optional[ChatModel]:
        stmt = select(self.model).where(
            self.model.id == chat_id,
            self.model.is_closed.is_(False),
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()