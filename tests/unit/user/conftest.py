import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from app.core.config.client.test.dto import user_test_conf
from app.core.config.client.otp.test.dto import otp_test_conf
from app.client.db.repositories.otp_redis import UserOtpRedisREPO
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO

@pytest.fixture
def fake_user_repository() -> UserSQLAlchemyREPO:
    fake = Mock(spec=UserSQLAlchemyREPO)

    fake.get_by_email_and_active = AsyncMock()
    fake.get_by_email = AsyncMock()
    fake.get_by_email_and_inactive = AsyncMock()

    return fake


@pytest.fixture
def fake_otp_repository() -> UserOtpRedisREPO:
    fake = Mock(spec=UserOtpRedisREPO)

    fake.get_by_email = AsyncMock()
    fake.save = AsyncMock()

    return fake


@pytest.fixture
def fake_user():
    user = MagicMock()
    user.email = user_test_conf.email
    user.password = user_test_conf.password
    user.is_active = user_test_conf.is_active

    return user


@pytest.fixture
def fake_otp():
    otp = MagicMock()
    otp.owner = user_test_conf.email
    otp.code = otp_test_conf.code
    otp.ttl = otp_test_conf.ttl
    
    return otp