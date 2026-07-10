from app.core.config.support.redis.cache.user_schat import chat_schat_cache_key, user_chat_cache_key
from app.core.config.support.redis.pubsub import schat_channel
from app.core.config.support.redis.keys.schat_active_msg import user_active_msg_chat_key
from app.shared.service.infrastructure.base import is_exists
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.redis.clients import RedisClient
from app.shared.service.infrastructure.redis.pubsub import RedisPubsub
from app.support.api.responses.websoket import WSMessageKeysEnum, WSMessageTypeEnum
from app.support.db.sqlalchemy.repositories.chat import ChatSQLAlchemyRepository
from app.support.exceptions.chat import ChatNotFound
from app.support.services.chat.close import close_chat

class CloseChatUC:
    def __init__(self,
        transaction: SQLAlchemyTransaction,
        redis_keyspace: RedisClient,
        redis_pubsub: RedisPubsub,
        chat_repository: ChatSQLAlchemyRepository,
    ):
        self._transaction = transaction
        self.redis_pubsub = redis_pubsub
        self.redis_keyspace = redis_keyspace
        self.chat_repository = chat_repository
    
    async def by_user(self, user_id: int) -> None:
        try:
            chat = await is_exists(
                self.chat_repository.get_by_user_id(user_id=user_id),
                ChatNotFound(),
            )

            close_chat(chat)
            await self._transaction.commit()

            await self.redis_keyspace.key.remove(user_chat_cache_key(user_id))
            await self.redis_keyspace.key.remove(chat_schat_cache_key(chat.id))
        except ChatNotFound:
            await self.redis_keyspace.key.remove(user_chat_cache_key(user_id))
            await self.redis_keyspace.key.remove(user_active_msg_chat_key(user_id))
            return

        await self.redis_pubsub.publish(schat_channel(chat.id), {
            WSMessageKeysEnum.TYPE: WSMessageTypeEnum.SYSTEM,
            "data": "chat is closed by user"
        })

    async def by_manager(self, chat_id: int) -> None:
        try:
            chat = await is_exists(
                self.chat_repository.get_by_is_not_closed(chat_id=chat_id),
                ChatNotFound(),
            )
            user_id = chat.user_id

            close_chat(chat)
            await self._transaction.commit()

            await self.redis_keyspace.key.remove(user_chat_cache_key(user_id))
            await self.redis_keyspace.key.remove(chat_schat_cache_key(chat_id))
        except ChatNotFound:
            await self.redis_keyspace.key.remove(chat_schat_cache_key(chat_id))
            return

        await self.redis_pubsub.publish(schat_channel(chat.id), {
            WSMessageKeysEnum.TYPE: WSMessageTypeEnum.SYSTEM,
            "data": "chat is closed by manager"
        })