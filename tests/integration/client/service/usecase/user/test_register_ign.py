import pytest
import uuid
from unittest.mock import patch
from app.client.api.requests.user.register import UserRegisterREQT
from app.client.exception.user.exists import UserAlreadyExistsERR
from app.client.exception.otp.expire import OtpNotExpiredERR
from app.client.dto.otp.base import OtpDTO
from app.client.service.infrastructure.otp.auth_session import otp_generate_session_id
from app.core.config.base import get_settings
from app.client.service.infrastructure.user.check_password import user_check_password
from app.core.config.client.otp.test.dto import otp_test_conf
from app.core.config.client.test.dto import user_test_conf

settings = get_settings()

@pytest.mark.asyncio
@patch("app.client.service.usecase.user.authentication.send_otp_email.kiq")
async def test_user_register_success(
    mock_send_email,
    user_authentication_usecase,
    user_register_reqt,
    user_repository,
    otp_auth_session,
    clean_redis,
):
    otp_session_id = await user_authentication_usecase.register(
        user_register_reqt
    )
    assert otp_session_id is not None

    user = await user_repository.get_by_email(
        user_register_reqt.email
    )
    assert user is not None
    assert user.email == user_register_reqt.email
    assert user.username == user_register_reqt.username
    assert user.is_active is False
    assert user_check_password(user_register_reqt.password, user.password)

    mock_send_email.assert_called_once()
    args, _ = mock_send_email.call_args
    email, otp_code = args
    assert email == user_register_reqt.email
    assert otp_code.isdigit()
    assert len(otp_code) == settings.otp.length

    otp = await otp_auth_session.get_by_owner(
        owner=user_register_reqt.email
    )
    assert otp is not None
    assert otp.owner == user_register_reqt.email
    assert otp.code == otp_code
    assert otp.session_id == otp_session_id


@pytest.mark.asyncio
async def test_user_register_user_already_exists(
    user_authentication_usecase,
    user_register_reqt,
    user_db,
):
    with pytest.raises(UserAlreadyExistsERR):
        await user_authentication_usecase.register(
            user_register_reqt
        )


@pytest.mark.asyncio
async def test_user_register_otp_not_expired(
    user_authentication_usecase,
    user_register_reqt,
    otp_auth_session,
    clean_redis,
):
    await otp_auth_session.create(
        OtpDTO(
            owner=user_register_reqt.email,
            code=otp_test_conf.code,
            session_id=otp_generate_session_id(),
            ttl=otp_test_conf.ttl,
        )
    )

    with pytest.raises(OtpNotExpiredERR):
        await user_authentication_usecase.register(
            user_register_reqt
        )


@pytest.mark.asyncio
@patch("app.client.service.usecase.user.authentication.send_otp_email.kiq")
async def test_user_register_update_credentials(
    mock_send_email,
    user_authentication_usecase,
    user_repository,
    inactive_user_db,
    clean_redis,
):
    user_data = UserRegisterREQT(
        email=user_test_conf.email,
        username=user_test_conf.username,
        password="Newpassword1243$",
    )

    otp_session_id = await user_authentication_usecase.register(
        user_data
    )
    assert otp_session_id is not None

    user = await user_repository.get_by_email(user_data.email)
    assert user is not None

    assert user_check_password(user_data.password, user.password)
    assert user.username == user_data.username
    assert user.is_active is False
    assert user.id == inactive_user_db.id