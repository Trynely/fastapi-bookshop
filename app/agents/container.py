from dishka import Provider, Scope, provide
from langchain_openai import ChatOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.db.repositories.books import AgentBooksSQLAlchemyREPO
from app.agents.llm import AgentLLMFactory
from app.agents.memory import RedisAgentChatHistory, ShownBooksTracker
from app.agents.cache import AgentAnswerCache
from app.agents.ratelimit import AgentRateLimiter
from app.agents.service import AgentChatService
from app.core.config.base import Settings
from app.order.db.sqlalchemy.repositories.cart import (
    CartItemSQLAlchemyRepository,
    CartSQLAlchemyRepository,
)
from app.order.db.sqlalchemy.repositories.order import OrderSQLAlchemyRepository
from app.order.usecase.cart.add_item import AddBookToCart
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.shared.db.postgres.repositories.sqlalchemy.transaction import (
    SQLAlchemyTransaction,
)
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder
from app.shared.service.infrastructure.redis.clients import RedisClient


class AgentProvider(Provider):
    scope = Scope.REQUEST

    @provide(scope=Scope.APP)
    def llm_factory(self, settings: Settings) -> AgentLLMFactory:
        return AgentLLMFactory(settings)

    @provide
    def agent_books_repo(
        self,
        session: AsyncSession,
    ) -> AgentBooksSQLAlchemyREPO:
        return AgentBooksSQLAlchemyREPO(session)

    @provide
    def order_repo(
        self,
        session: AsyncSession,
    ) -> OrderSQLAlchemyRepository:
        return OrderSQLAlchemyRepository(session)

    @provide
    def cart_repo(
        self,
        session: AsyncSession,
    ) -> CartSQLAlchemyRepository:
        return CartSQLAlchemyRepository(session)

    @provide
    def add_to_cart_uc(
        self,
        session: AsyncSession,
        transaction: SQLAlchemyTransaction,
    ) -> AddBookToCart:
        return AddBookToCart(
            transaction=transaction,
            book_repository=BookSQLAlchemyREPO(session),
            cart_repository=CartSQLAlchemyRepository(session),
            cart_item_repository=CartItemSQLAlchemyRepository(session),
        )

    @provide
    def chat_history(
        self,
        redis: RedisClient,
    ) -> RedisAgentChatHistory:
        return RedisAgentChatHistory(redis)

    @provide
    def shown_books_tracker(
        self,
        redis: RedisClient,
    ) -> ShownBooksTracker:
        return ShownBooksTracker(redis)

    @provide
    def rate_limiter(
        self,
        redis: RedisClient,
    ) -> AgentRateLimiter:
        return AgentRateLimiter(redis)

    @provide
    def answer_cache(
        self,
        redis: RedisClient,
    ) -> AgentAnswerCache:
        return AgentAnswerCache(redis)

    @provide
    def agent_chat_service(
        self,
        llm_factory: AgentLLMFactory,
        embedder: OllamaEmbedder,
        books_qdrant_repo: BooksQdrantREPO,
        agent_books_repo: AgentBooksSQLAlchemyREPO,
        order_repo: OrderSQLAlchemyRepository,
        add_to_cart_uc: AddBookToCart,
        history: RedisAgentChatHistory,
        shown_books: ShownBooksTracker,
        cart_repo: CartSQLAlchemyRepository,
        rate_limiter: AgentRateLimiter,
        answer_cache: AgentAnswerCache,
    ) -> AgentChatService:
        return AgentChatService(
            llm_factory=llm_factory,
            embedder=embedder,
            books_qdrant_repo=books_qdrant_repo,
            agent_books_repo=agent_books_repo,
            order_repo=order_repo,
            add_to_cart_uc=add_to_cart_uc,
            history=history,
            shown_books=shown_books,
            cart_repo=cart_repo,
            rate_limiter=rate_limiter,
            answer_cache=answer_cache,
        )
