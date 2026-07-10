from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO
from app.support.models import ChatMessageModel, ChatModel

class ChatMsgSQLAlchemyRepository(BaseSQLAlchemyREPO[ChatMessageModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=ChatMessageModel,
        )

    async def get_list_by_chat_and_user_id(self, user_id: int) -> List[ChatMessageModel]:
        stmt = (
            select(self.model).join(
                ChatModel, self.model.chat_id == ChatModel.id
            ).where(
                ChatModel.user_id == int(user_id)
            ).order_by(ChatMessageModel.created_at)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()