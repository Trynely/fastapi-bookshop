from typing import Optional

from app.core.config.support.redis.cache.user_schat import USER_SCHAT_CACHE_TTL, user_chat_cache_key
from app.shared.service.infrastructure.base import is_exists
from app.shared.db.redis import redis_cache
from app.support.api.responses.chat import ChatRead
from app.support.db.sqlalchemy.repositories.chat import ChatSQLAlchemyRepository
from app.support.exceptions.chat import ChatNotFound
from app.support.models import ChatModel

class ChatFilterQH:
    def __init__(self, chat_repository: ChatSQLAlchemyRepository):
        self.chat_repository = chat_repository
    
    @redis_cache(key_builder=user_chat_cache_key, ttl=USER_SCHAT_CACHE_TTL, response_model=ChatRead)
    async def get_or_create_user_chat(self, user_id: int) -> ChatModel:
        try:
            chat = await is_exists(
                self.chat_repository.get_by_user_id(user_id=int(user_id)),
                ChatNotFound(),
            )
        except ChatNotFound:
            new_chat = ChatModel(user_id=int(user_id))
            chat = await self.chat_repository.save(new_chat)
            await self.chat_repository.session.commit()
        
        return ChatRead.model_validate(chat)