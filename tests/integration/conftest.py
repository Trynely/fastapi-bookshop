import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
)
from sqlalchemy.pool import NullPool
from app.core.app_factory import create_app
from app.core.config.base import get_settings
from app.core.db.models.base import Base
from app.core.db.redis import get_redis
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from httpx import ASGITransport, AsyncClient
from dishka import make_async_container
from dishka.integrations.fastapi import setup_dishka
from app.product.container import BookProvider
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.container import DBProvider, TestDBProvider
from app.client.container import ClientProvider

from tests.integration.fixtures.models import *
from tests.integration.fixtures.repositories import *
from tests.integration.fixtures.requests import *
from tests.integration.fixtures.services.infrastructure import *
from tests.integration.fixtures.services.usecase import *


settings = get_settings()

# -------------------- FastAPI app --------------------

@pytest.fixture(scope="function")
def app() -> FastAPI:
    return create_app()


# -------------------- Database --------------------

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        str(settings.test_db.url),
        poolclass=NullPool,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def setup_db(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def db_session(engine, setup_db):
    async with engine.connect() as conn:
        transaction = await conn.begin()

        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
        )

        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest_asyncio.fixture(scope="function")
async def transaction(db_session: AsyncSession):
    return SQLAlchemyTransaction(db_session)

# -------------------- Api Client --------------------

@pytest_asyncio.fixture(scope="function")
async def async_client(app: FastAPI, db_session: AsyncSession):
    container = make_async_container(
        DBProvider(),
        BookProvider(),
        ClientProvider(),
        TestDBProvider(),
        context={AsyncSession: db_session},
    )

    setup_dishka(container, app)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=f"{settings.app.host}{settings.api.prefix}"
    ) as client:
        yield client

    await container.close()

# -------------------- Redis --------------------

@pytest_asyncio.fixture(scope="function")
async def redis_connection():
    redis = await get_redis()
    yield redis
    await redis.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_redis(redis_connection):
    await redis_connection.flushdb()
    yield