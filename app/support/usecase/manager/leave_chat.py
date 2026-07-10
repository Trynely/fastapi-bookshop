from app.core.config.support.redis.cache.user_schat import user_chat_cache_key
from app.core.config.support.redis.pubsub import schat_channel
from app.shared.service.infrastructure.base import is_exists
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.redis.clients import RedisClient
from app.shared.service.infrastructure.redis.pubsub import RedisPubsub
from app.support.api.responses.websoket import WSMessageKeysEnum, WSMessageTypeEnum
from app.support.db.sqlalchemy.repositories.chat import ChatSQLAlchemyRepository
from app.support.exceptions.chat import ChatNotFound
from app.support.exceptions.manager import ManagerNotAssigned
from app.support.services.chat.assign_manager import unassign_manager_from_chat
from app.support.services.manager.check_reassign import check_same_manager

class ManagerLeaveChatUC:
    def __init__(self,
        transaction: SQLAlchemyTransaction,
        redis_keyspace: RedisClient,
        redis_pubsub: RedisPubsub,
        chat_repository: ChatSQLAlchemyRepository,
    ):
        self._transaction = transaction
        self.redis_keyspace = redis_keyspace
        self.redis_pubsub = redis_pubsub
        self.chat_repository = chat_repository

    async def execute(self, manager_id: int, chat_id: int) -> None:
        chat = await is_exists(
            self.chat_repository.get_by_is_not_closed(chat_id=chat_id),
            ChatNotFound(),
        )

        if not check_same_manager(chat=chat, manager_id=manager_id):
            raise ManagerNotAssigned()

        unassign_manager_from_chat(chat)
        await self._transaction.commit()

        await self.redis_keyspace.key.remove(user_chat_cache_key(chat.user_id))

        await self.redis_pubsub.publish(schat_channel(chat_id), {
            WSMessageKeysEnum.TYPE: WSMessageTypeEnum.SYSTEM,
            "data": "менеджер покинул чат, вы возвращены в очередь"
        })
