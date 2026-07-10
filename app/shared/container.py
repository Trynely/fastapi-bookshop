from typing import AsyncIterable
import aiohttp
from dishka import Provider, Scope, from_context, provide
import httpx
from elasticsearch import AsyncElasticsearch
from sqlalchemy.ext.asyncio import AsyncSession
from qdrant_client import AsyncQdrantClient
from app.client.db.qdrant.collections.user_reco_profile import UserRecoProfileQdrantCollection
from app.core.config.base import Settings, get_settings
from app.core.config.shared.qdrant.embedding import BGE_M3_EMBEDDING_MODEL
from app.core.db.postgres import DatabaseHelper
from app.product.db.elasticsearch.indexes.books import BooksElasticIndex
from app.product.db.qdrant.collections.books import BooksQdrantCollection
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
import redis.asyncio as redis
from app.core.config.base import get_settings
from app.shared.db.elasticsearch.indexes.initializer import ElasticIndexInitializer
from app.shared.db.qdrant.collections.intializer import QdrantCollectionInitializer
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder
from app.support.db.qdrant.collections.faq import FaqQdrantCollection
from app.shared.service.infrastructure.redis.clients import RedisClient
from app.shared.service.infrastructure.redis.pubsub import RedisPubsub

settings = get_settings()

class DBProvider(Provider):
    scope = Scope.APP

    @provide
    def db_helper(self) -> DatabaseHelper:
        settings = get_settings()
        
        return DatabaseHelper(
            url=str(settings.db.url),
            echo=settings.db.echo,
            echo_pool=settings.db.echo_pool,
            pool_size=settings.db.pool_size,
            max_overflow=settings.db.max_overflow,
        )

    @provide(scope=Scope.REQUEST)
    async def session(
        self,
        db_helper: DatabaseHelper,
    ) -> AsyncIterable[AsyncSession]:
        async with db_helper.session_factory() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def transaction(
        self,
        session: AsyncSession,
    ) -> SQLAlchemyTransaction:
        return SQLAlchemyTransaction(session)


class TestDBProvider(Provider):
    scope = Scope.APP

    session_override = from_context(
        provides=AsyncSession, 
        scope=Scope.APP,
        override=True
    )


class RedisProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_redis(self) -> AsyncIterable[redis.Redis]:
        settings = get_settings()
        
        client = redis.from_url(
            settings.redis.url,
            encoding="utf-8",
            decode_responses=True,
        )
        yield client
        await client.connection_pool.disconnect()

    @provide(scope=Scope.SESSION)
    def get_pubsub(self, redis_connection: redis.Redis) -> RedisPubsub:
        return RedisPubsub(redis_connection)
    
    @provide(scope=Scope.REQUEST)
    def get_redis_connection(self, redis_connection: redis.Redis) -> RedisClient:
        return RedisClient(redis_connection)


class QdrantProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_qdrant(self) -> AsyncIterable[AsyncQdrantClient]:
        settings = get_settings()

        client = AsyncQdrantClient(url=settings.qdrant.url)
        yield client
        await client.close()

    
    @provide(scope=Scope.APP)
    def qdrant_collection_initializer(
        self,
        books_collection: BooksQdrantCollection,
        user_reco_profile_collection: UserRecoProfileQdrantCollection,
        faq_collection: FaqQdrantCollection,
    ) -> QdrantCollectionInitializer:
        return QdrantCollectionInitializer(
            collections=[
                books_collection,
                user_reco_profile_collection,
                faq_collection,
            ]
        )


class ElasticsearchProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_elasticsearch(self) -> AsyncIterable[AsyncElasticsearch]:
        settings = get_settings()

        client = AsyncElasticsearch(hosts=settings.elasticsearch.url)
        yield client
        await client.close()

    @provide(scope=Scope.APP)
    def elastic_index_initializer(
        self,
        books_index: BooksElasticIndex,
    ) -> ElasticIndexInitializer:
        return ElasticIndexInitializer(
            indexes=[
                books_index,
            ]
        )


class HttpClientProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_session(self) -> AsyncIterable[aiohttp.ClientSession]:
        async with aiohttp.ClientSession() as session:
            yield session


class SettingsProvider(Provider):
    @provide(scope=Scope.APP)
    def settings_factory(self) -> Settings:
        return get_settings()


class OllamaProvider(Provider):
    @provide(scope=Scope.APP)
    async def http_client(self) -> AsyncIterable[httpx.AsyncClient]:
        async with httpx.AsyncClient(
            base_url=settings.ollama.url,
            timeout=httpx.Timeout(
                connect=5.0,
                read=150.0,
                write=150.0,
                pool=5.0,
            ),
        ) as client:
            yield client

    @provide(scope=Scope.APP)
    def bge_embedder(
        self,
        client: httpx.AsyncClient,
    ) -> OllamaEmbedder:
        return OllamaEmbedder(
            client=client,
            model=BGE_M3_EMBEDDING_MODEL,
        )


shared_providers = [
    DBProvider(),
    RedisProvider(),
    QdrantProvider(),
    ElasticsearchProvider(),
    OllamaProvider(),
    HttpClientProvider(),
    SettingsProvider(),
]