import pytest
import pytest_asyncio
from app.client.service.infrastructure.jwt.refresh_session import JWTRefreshAuthSession
from app.client.service.infrastructure.otp.auth_session import OtpAuthSession
from app.core.config.base import get_settings
from app.client.service.infrastructure.jwt.generator import JWTGenerator
from app.shared.service.infrastructure.redis.clients import RedisClient

# client
@pytest_asyncio.fixture(scope="function")
async def otp_auth_session(redis_connection):
    settings = get_settings()
    redis_wrapper = RedisClient(redis_connection)

    return OtpAuthSession(
        redis=redis_wrapper,
        settings=settings,
    )


@pytest_asyncio.fixture(scope="function")
async def jwt_refresh_session(redis_connection):
    redis_wrapper = RedisClient(redis_connection)
    return JWTRefreshAuthSession(redis_connection=redis_wrapper)


@pytest.fixture
def jwt_generator():
    return JWTGenerator()