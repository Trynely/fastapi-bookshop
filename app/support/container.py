import aiohttp
from dishka import (
    Provider,
    provide,
    Scope,
)
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config.shared.qdrant.collections import QDRANT_COLLECTION_NAME
from app.shared.db.qdrant.base_repository import BaseQdrantREPO
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.redis.clients import RedisClient
from app.shared.service.infrastructure.redis.pubsub import RedisPubsub
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder
from app.support.db.qdrant.collections.faq import FaqQdrantCollection
from app.support.db.sqlalchemy.repositories.chat import ChatSQLAlchemyRepository
from app.support.db.sqlalchemy.repositories.chat_messages import ChatMsgSQLAlchemyRepository
from app.support.db.sqlalchemy.repositories.manager import ManagerSQLAlchemyRepository
from app.support.usecase.bot_answer import BotAnswerUC
from app.support.usecase.close import CloseChatUC
from app.support.usecase.escalation import ChatEscalationUC
from app.support.usecase.manager.assign_to_chat import AssignManagerToChatUC
from app.support.usecase.manager.handle_messages import HandleManagerMessageUC
from app.support.usecase.manager.leave_chat import ManagerLeaveChatUC
from app.support.usecase.query_handlers.filter import ChatFilterQH
from app.support.usecase.query_handlers.manager.filter import ManagerFilterQH
from app.support.usecase.query_handlers.messages.filter import ChatMessagesFilterQH

class ChatProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def chat_repository(
        self,
        session: AsyncSession,
    ) -> ChatSQLAlchemyRepository:
        return ChatSQLAlchemyRepository(session)

    @provide
    def chat_filter_qh(
        self,
        chat_repository: ChatSQLAlchemyRepository
    ) -> ChatFilterQH:
        return ChatFilterQH(chat_repository=chat_repository)
    
    @provide
    def close_chat_usecase(
        self,
        transaction: SQLAlchemyTransaction,
        redis_keyspace: RedisClient,
        redis_pubsub: RedisPubsub,
        chat_repository: ChatSQLAlchemyRepository,
    ) -> CloseChatUC:
        return CloseChatUC(
            transaction=transaction,
            redis_pubsub=redis_pubsub,
            chat_repository=chat_repository,
            redis_keyspace=redis_keyspace,
        )
    
    @provide
    def chat_escalation_usecase(
        self,
        redis_keyspace: RedisClient,
        redis_pubsub: RedisPubsub,
        transaction: SQLAlchemyTransaction,
        chat_repository: ChatSQLAlchemyRepository,
        message_repository: ChatMsgSQLAlchemyRepository,
    ) -> ChatEscalationUC:
        return ChatEscalationUC(
            transaction=transaction,
            redis_keyspace=redis_keyspace,
            redis_pubsub=redis_pubsub,
            chat_repository=chat_repository,
            message_repository=message_repository,
        )


class ChatMsgProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def chat_msg_repository(
        self,
        session: AsyncSession,
    ) -> ChatMsgSQLAlchemyRepository:
        return ChatMsgSQLAlchemyRepository(session)

    @provide
    def chat_messages_filter_qh(
        self,
        message_repository: ChatMsgSQLAlchemyRepository
    ) -> ChatMessagesFilterQH:
        return ChatMessagesFilterQH(
            message_repository=message_repository
        )
    
    @provide(scope=Scope.APP)
    def faq_qdrant_collection(
        self,
        client: AsyncQdrantClient,
        embedder: OllamaEmbedder,
    ) -> FaqQdrantCollection:
        return FaqQdrantCollection(
            qdrant_client=client,
            embedder=embedder,
        )

    @provide
    def faq_qdrant_repository(self, client: AsyncQdrantClient) -> BaseQdrantREPO:
        return BaseQdrantREPO(
            qdrant_client=client,
            collection_name=QDRANT_COLLECTION_NAME
        )
    
    @provide
    def bot_answer_uc(
        self,
        chat_repository: ChatSQLAlchemyRepository,
        message_repository: ChatMsgSQLAlchemyRepository,
        transaction: SQLAlchemyTransaction,
        redis_pubsub: RedisPubsub,
        faq_qdrant_repository: BaseQdrantREPO,
        http_client: aiohttp.ClientSession,
    ) -> BotAnswerUC:
        return BotAnswerUC(
            chat_repository=chat_repository,
            message_repository=message_repository,
            redis_pubsub=redis_pubsub,
            faq_qdrant_repository=faq_qdrant_repository,
            transaction=transaction,
            http_client=http_client
        )
    

class ManagerProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def manager_repository(
        self,
        session: AsyncSession,
    ) -> ManagerSQLAlchemyRepository:
        return ManagerSQLAlchemyRepository(session)

    @provide
    def manager_filter_qh(
        self,
        manager_repository: ManagerSQLAlchemyRepository
    ) -> ManagerFilterQH:
        return ManagerFilterQH(
            manager_repository=manager_repository
        )
    
    @provide
    def assign_manager_to_chat_uc(
        self,
        transaction: SQLAlchemyTransaction,
        redis_keyspace: RedisClient,
        redis_pubsub: RedisPubsub,
        chat_repository: ChatSQLAlchemyRepository,
        manager_repository: ManagerSQLAlchemyRepository,
    ) -> AssignManagerToChatUC:
        return AssignManagerToChatUC(
            chat_repository=chat_repository,
            redis_keyspace=redis_keyspace,
            redis_pubsub=redis_pubsub,
            transaction=transaction,
            manager_repository=manager_repository,
        )
    
    @provide
    def manager_leave_chat_uc(
        self,
        transaction: SQLAlchemyTransaction,
        redis_keyspace: RedisClient,
        redis_pubsub: RedisPubsub,
        chat_repository: ChatSQLAlchemyRepository,
    ) -> ManagerLeaveChatUC:
        return ManagerLeaveChatUC(
            transaction=transaction,
            redis_keyspace=redis_keyspace,
            redis_pubsub=redis_pubsub,
            chat_repository=chat_repository,
        )

    @provide
    def handle_manager_message_uc(
        self,
        redis_keyspace: RedisClient,
        redis_pubsub: RedisPubsub,
        transaction: SQLAlchemyTransaction,
        chat_repository: ChatSQLAlchemyRepository,
        message_repository: ChatMsgSQLAlchemyRepository,
    ) -> HandleManagerMessageUC:
        return HandleManagerMessageUC(
            transaction=transaction,
            redis_keyspace=redis_keyspace,
            redis_pubsub=redis_pubsub,
            chat_repository=chat_repository,
            message_repository=message_repository,
        )
    

support_providers = [
    ChatProvider(),
    ChatMsgProvider(),
    ManagerProvider(),
]