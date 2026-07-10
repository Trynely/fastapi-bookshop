from app.support.db.sqlalchemy.repositories.chat_messages import ChatMsgSQLAlchemyRepository
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_serializer

class ChatMessageSchema(BaseModel):
    sender: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()


class ChatMessagesFilterQH:
    def __init__(self, message_repository: ChatMsgSQLAlchemyRepository):
        self.message_repository = message_repository
    
    async def get_user_chat_history(self, user_id: int):
        history_messages = await self.message_repository.get_list_by_chat_and_user_id(user_id=user_id)

        return [
            ChatMessageSchema.model_validate(msg).model_dump()
            for msg in history_messages
        ]