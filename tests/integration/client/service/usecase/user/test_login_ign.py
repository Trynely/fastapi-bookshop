import pytest
from unittest.mock import patch
from app.client.exception.otp.expire import OtpNotExpiredERR
from app.client.exception.user.invalid_creds import UserInvalidCredentialsERR
from app.client.service.infrastructure.otp.auth_session import otp_generate_session_id
from app.core.config.client.test.dto import user_test_conf
from app.core.config.client.otp.test.dto import otp_test_conf
from app.client.dto.otp.base import OtpDTO
from app.core.config.base import get_settings

settings = get_settings()

@pytest.mark.asyncio
@patch("app.client.service.usecase.user.authentication.send_otp_email.kiq")
async def test_user_login_success(
    mock_send_email,
    user_authentication_usecase,
    user_login_reqt,
    user_db,
    clean_redis, 
    otp_auth_session,
):
    otp_session_id = await user_authentication_usecase.login(
        user_login_reqt
    )
    assert otp_session_id is not None

    mock_send_email.assert_called_once()
    args, _ = mock_send_email.call_args
    email, otp_code = args

    assert email == user_login_reqt.email
    assert otp_code.isdigit()
    assert len(otp_code) == settings.otp.length

    otp = await otp_auth_session.get_by_owner(
        owner=user_login_reqt.email
    )
    assert otp is not None
    assert otp.owner == user_login_reqt.email
    assert otp.code == otp_code
    assert otp.session_id == otp_session_id


@pytest.mark.asyncio
async def test_user_login_invalid_creds(
    user_authentication_usecase,
):
    request = {
        "email": "notfound@example.com",
        "password": user_test_conf.password,
    }

    with pytest.raises(UserInvalidCredentialsERR):
        await user_authentication_usecase.login(
            type("Req", (), request)()
        )


@pytest.mark.asyncio
async def test_user_login_otp_not_expired(
    user_authentication_usecase,
    otp_auth_session,
    user_login_reqt,
    user_db,
    clean_redis,
):
    await otp_auth_session.create(
        OtpDTO(
            owner=user_login_reqt.email,
            code=otp_test_conf.code,
            session_id=otp_generate_session_id(),
            ttl=otp_test_conf.ttl,
        )
    )

    with pytest.raises(OtpNotExpiredERR):
        await user_authentication_usecase.login(
            user_login_reqt
        )