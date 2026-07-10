from typing import Optional
from app.core.config.support.rabbitmq.routing_keys import LLM_QUEUE
from app.core.config.support.redis.cache.user_schat import USER_SCHAT_CACHE_TTL, user_chat_cache_key
from app.core.config.support.redis.keys.rate_limit_schat import RATE_LIMIT_MSG_SCHAT_TTL, rate_limit_msg_schat_key
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
from app.support.dto.events.user_msg import ChatUserMsgEVT
from app.support.exceptions.chat import ChatNotFound
from app.support.exceptions.message import TooManySChatMessages
from app.support.models import ChatMessageModel, ChatMessageSender, ChatModel
from app.support.services.chat.escalation import chat_is_escalated, detect_chat_escalation, escalate_chat
from app.support.services.chat.last_message import touch_chat_last_message

class ChatEscalationUC:
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
        await self.redis_keyspace.set(
            user_active_msg_chat_key(user_id),
            str(user_id),
            ex=USER_ACTIVE_MSG_SCHAT_TLL,
        )

    async def _check_escalation(self, chat: ChatModel, user_text: str) -> bool:
        escalation_reason = detect_chat_escalation(user_text)
                
        if escalation_reason and not chat_is_escalated(chat):
            escalate_chat(chat, escalation_reason)
            return True
        
        return False
    
    async def _check_user_rate_limit(self, user_id: int) -> bool:
        key = rate_limit_msg_schat_key(user_id)

        count = await self.redis_keyspace.incr(key)

        if count == 1:
            await self.redis_keyspace.expire(key, RATE_LIMIT_MSG_SCHAT_TTL)
        if count > 5:
            raise TooManySChatMessages()

        return True
    
    @redis_cache(key_builder=user_chat_cache_key, ttl=USER_SCHAT_CACHE_TTL, response_model=ChatRead)
    async def __user_chat(self, user_id: int) -> Optional[ChatRead]:
        chat = await is_exists(
            self.chat_repository.get_by_user_id(user_id=user_id),
            ChatNotFound(),
        )
        return ChatRead.model_validate(chat)
    
    async def handle_user_message(self, user_id: int, user_text: str) -> None:
        await self._check_user_rate_limit(user_id=user_id)

        chat = await self.__user_chat(user_id)
        await self._touch_chat_idle(user_id)

        message = ChatMessageModel(
            chat_id=chat.id,
            sender=ChatMessageSender.USER,
            content=user_text
        )
        await self.message_repository.save(message)
        touch_chat_last_message(chat)
        
        escalated = await self._check_escalation(chat, user_text)

        await self._transaction.commit()

        if escalated:
            await self.redis_pubsub.publish(schat_channel(chat.id), {
                WSMessageKeysEnum.TYPE: WSMessageTypeEnum.SYSTEM,
                "data": "chat has been transferred to the operator"
            })
        
        await self.redis_pubsub.publish(schat_channel(chat.id), {
            WSMessageKeysEnum.TYPE: WSMessageTypeEnum.MESSAGE,
            "data": {
                "sender": "user",
                "content": user_text
            }
        })
        
        if not chat_is_escalated(chat) and not chat.manager_id:
            event = ChatUserMsgEVT(
                chat_id=chat.id,
                message=user_text,
            )
            # await publish_message_rmq(
            #     event=event,
            #     routing_key=LLM_QUEUE,
            # )