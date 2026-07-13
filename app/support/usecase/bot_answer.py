import aiohttp
from app.core.config.shared.llm.failed import LLM_FAILED
from app.core.config.shared.qdrant.embedding import BGE_M3_EMBEDDING_MODEL
from app.core.config.support.llm.prompt import LLM_FAQ_PROMPT
from app.core.config.support.redis.pubsub import schat_channel
from app.shared.db.qdrant.base_repository import BaseQdrantREPO
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.redis.pubsub import RedisPubsub
from app.support.api.responses.websoket import WSMessageKeysEnum, WSMessageTypeEnum
from app.support.db.sqlalchemy.repositories.chat import ChatSQLAlchemyRepository
from app.support.db.sqlalchemy.repositories.chat_messages import ChatMsgSQLAlchemyRepository
from app.support.infrastructure.llm.generate_answer import send_to_llm
from app.support.infrastructure.qdrant.embedding import get_embedding
from app.support.models import ChatMessageModel, ChatMessageSender

class BotAnswerUC:
    def __init__(
        self,
        chat_repository: ChatSQLAlchemyRepository,
        message_repository: ChatMsgSQLAlchemyRepository,
        transaction: SQLAlchemyTransaction,
        redis_pubsub: RedisPubsub,
        faq_qdrant_repository: BaseQdrantREPO,
        http_client: aiohttp.ClientSession,
    ):
        self._transaction = transaction
        self.chat_repository = chat_repository
        self.message_repository = message_repository
        self.redis_pubsub = redis_pubsub
        self.faq_qdrant_repository = faq_qdrant_repository
        self._http_client = http_client

    async def generate(self, user_message: str, chat_id: int) -> str:
        query_vector = await get_embedding(
            text=user_message,
            embedding_model=BGE_M3_EMBEDDING_MODEL,
            http_client=self._http_client,
        )
        
        context = await self.faq_qdrant_repository.get_context(query_vector)
        answer = ""

        if context:
            prompt = LLM_FAQ_PROMPT.format(
                context=context, 
                user_message=user_message
            )

            answer = await send_to_llm(
                http_client=self._http_client,
                prompt=prompt,
            )
        else:
            answer = LLM_FAILED
        
        bot_message = ChatMessageModel(
            chat_id=chat_id,
            sender=ChatMessageSender.BOT,
            content=answer,
        )

        await self.message_repository.save(bot_message)
        await self.chat_repository.update_last_message_at(chat_id=chat_id)
        await self._transaction.commit()

        await self.redis_pubsub.publish(schat_channel(chat_id), {
            WSMessageKeysEnum.TYPE: WSMessageTypeEnum.MESSAGE,
            "data": {"sender": "bot", "content": answer}
        })