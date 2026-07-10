from typing import Optional
from app.core.config.support.redis.cache.user_schat import USER_SCHAT_CACHE_TTL, chat_schat_cache_key
from app.core.config.support.redis.pubsub import schat_channel
from app.core.config.support.redis.keys.schat_active_msg import USER_ACTIVE_MSG_SCHAT_TLL, user_active_msg_chat_key
from app.shared.service.infrastructure.base import is_exists
from app.shared.db.redis import redis_cache
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.redis.clients import RedisClient
from app.shared.service.infrastructure.redis.pubsub import RedisPubsub
from app.support.api.responses.chat import ChatRead
from app.support.api.responses.websoket import WSMessageKeysEnum, WSMessageTypeEnum
from app.support.db.sqlalchemy.repositories.chat import ChatSQLAlchemyRepository
from app.support.db.sqlalchemy.repositories.chat_messages import ChatMsgSQLAlchemyRepository
from app.support.exceptions.chat import ChatNotFound
from app.support.models import ChatMessageModel, ChatMessageSender

class HandleManagerMessageUC:
    def __init__(
        self,
        redis_keyspace: RedisClient,
        redis_pubsub: RedisPubsub,
        transaction: SQLAlchemyTransaction,
        chat_repository: ChatSQLAlchemyRepository,
        message_repository: ChatMsgSQLAlchemyRepository,
    ):
        self.redis_keyspace=redis_keyspace
        self.redis_pubsub = redis_pubsub
        self.message_repository = message_repository
        self.chat_repository = chat_repository
        self._transaction = transaction

    async def _touch_chat_idle(self, user_id: int):
        await self.redis_keyspace.string.add(
            user_active_msg_chat_key(user_id),
            str(user_id),
            ex=USER_ACTIVE_MSG_SCHAT_TLL,
        )
    
    @redis_cache(key_builder=chat_schat_cache_key, ttl=USER_SCHAT_CACHE_TTL, response_model=ChatRead)
    async def __user_chat(self, chat_id: int) -> Optional[ChatRead]:
        chat = await is_exists(
            self.chat_repository.get_by_is_not_closed(chat_id=chat_id),
            ChatNotFound(),
        )
        return ChatRead.model_validate(chat)
    
    async def execute(self, chat_id: int, manager_text: str) -> None:
        chat = await self.__user_chat(chat_id)
        await self._touch_chat_idle(user_id=chat.user_id)

        message = ChatMessageModel(
            chat_id=chat.id,
            sender=ChatMessageSender.MANAGER,
            content=manager_text
        )
        await self.message_repository.save(message)
        await self.chat_repository.update_last_message_at(chat_id=chat.id)
        await self._transaction.commit()
        
        await self.redis_pubsub.publish(schat_channel(chat.id), {
            WSMessageKeysEnum.TYPE: WSMessageTypeEnum.MESSAGE,
            "data": {
                "sender": "manager",
                "content": manager_text
            }
        })