from app.core.config.support.redis.pubsub import schat_channel
from app.shared.service.infrastructure.base import is_exists
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.redis.clients import RedisClient
from app.shared.service.infrastructure.redis.pubsub import RedisPubsub
from app.support.api.responses.websoket import WSMessageKeysEnum, WSMessageTypeEnum
from app.support.db.sqlalchemy.repositories.chat import ChatSQLAlchemyRepository
from app.support.db.sqlalchemy.repositories.manager import ManagerSQLAlchemyRepository
from app.support.exceptions.chat import ChatNotFound
from app.support.exceptions.manager import ManagerAlreadyAssigned, ManagerNotFound
from app.support.services.chat.assign_manager import assign_manager_to_chat
from app.support.services.manager.check_assing import chat_has_no_manager
from app.support.services.manager.check_reassign import check_same_manager

class AssignManagerToChatUC:
    def __init__(self,
        transaction: SQLAlchemyTransaction,
        redis_pubsub: RedisPubsub,
        chat_repository: ChatSQLAlchemyRepository,
        manager_repository: ManagerSQLAlchemyRepository,
    ):
        self._transaction = transaction
        self.redis_pubsub = redis_pubsub
        self.chat_repository = chat_repository
        self.manager_repository = manager_repository

    async def _send_redis_event(self, chat_id: int, manager_name: str):
        await self.redis_pubsub.publish(schat_channel(chat_id),
            {
                WSMessageKeysEnum.TYPE: WSMessageTypeEnum.SYSTEM,
                "data": f"{manager_name} подключился к чату и готов помочь"
            }
        )

    async def execute(self, manager_id: int, chat_id: int):
        manager = await is_exists(
            self.manager_repository.get_by_id(manager_id=manager_id),
            ManagerNotFound(),
        )

        chat = await is_exists(
            self.chat_repository.get_by_is_not_closed(chat_id=chat_id),
            ChatNotFound(),
        )

        if chat_has_no_manager(chat):
            assign_manager_to_chat(chat=chat, manager_id=manager_id)
            await self._transaction.commit()

            await self._send_redis_event(
                chat_id=chat_id,
                manager_name=manager.username,
            )
            return
        
        if check_same_manager(chat=chat, manager_id=manager_id):
            await self._send_redis_event(
                chat_id=chat_id,
                manager_name=manager.username,
            )
            return
        raise ManagerAlreadyAssigned()