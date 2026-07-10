import pytest
from app.client.api.requests.user.auth import UserAuthConfirmREQT
from app.client.exception.otp.expire import OtpExpiredERR
from app.client.exception.otp.invalid import OtpInvalidERR
from app.client.service.infrastructure.otp.auth_session import otp_generate_session_id
from app.client.dto.otp.base import OtpDTO
from app.client.exception.user.exists import UserNotFoundERR
from app.client.service.infrastructure.jwt.decode import jwt_decode
from app.core.config.base import get_settings
from app.core.config.client.otp.test.dto import otp_test_conf

settings = get_settings()

@pytest.mark.asyncio
async def test_user_register_confirm_success(
    user_authorization_usecase,
    inactive_user_db,
    otp_auth_session,
    jwt_refresh_session,
    clean_redis,
):
    otp = OtpDTO(
        owner=inactive_user_db.email,
        code=otp_test_conf.code,
        session_id=otp_generate_session_id(),
        ttl=otp_test_conf.ttl,
    )
    await otp_auth_session.create(otp)

    user_data = UserAuthConfirmREQT(
        session_id=otp.session_id,
        otp=otp.code,
    )

    tokens = await user_authorization_usecase.register_confirm(user_data)

    assert tokens.access_token
    assert tokens.refresh_token

    updated_user = await user_authorization_usecase.user_repository.get_by_email(
        inactive_user_db.email
    )

    assert updated_user.is_active is True

    otp = await otp_auth_session.get(otp.session_id)
    assert otp is None

    payload = jwt_decode(tokens.refresh_token)

    refresh_exists = await jwt_refresh_session.is_exists(payload.jti)
    assert refresh_exists is True


@pytest.mark.asyncio
async def test_user_register_confirm_invalid_code(
    user_authorization_usecase,
    inactive_user_db,
    otp_auth_session,
    clean_redis,
):
    otp = OtpDTO(
        owner=inactive_user_db.email,
        code=otp_test_conf.code,
        session_id=otp_generate_session_id(),
        ttl=otp_test_conf.ttl,
    )
    await otp_auth_session.create(otp)

    user_data = UserAuthConfirmREQT(
        session_id=otp.session_id,
        otp="000000",
    )

    with pytest.raises(OtpInvalidERR):
        await user_authorization_usecase.register_confirm(user_data)


@pytest.mark.asyncio
async def test_user_register_confirm_expired_session(
    user_authorization_usecase,
):
    user_data = UserAuthConfirmREQT(
        session_id=otp_generate_session_id(),
        otp=otp_test_conf.code,
    )

    with pytest.raises(OtpExpiredERR):
        await user_authorization_usecase.register_confirm(user_data)


@pytest.mark.asyncio
async def test_user_register_confirm_user_not_found(
    user_authorization_usecase,
    otp_auth_session,
    clean_redis,
):
    otp = OtpDTO(
        owner="unavailable@email.com",
        code=otp_test_conf.code,
        session_id=otp_generate_session_id(),
        ttl=otp_test_conf.ttl,
    )
    await otp_auth_session.create(otp)

    user_data = UserAuthConfirmREQT(
        session_id=otp.session_id,
        otp=otp.code,
    )

    with pytest.raises(UserNotFoundERR):
        await user_authorization_usecase.register_confirm(user_data)


@pytest.mark.asyncio
async def test_user_register_confirm_user_already_active(
    user_authorization_usecase,
    user_db,
    otp_auth_session,
    clean_redis,
):
    otp = OtpDTO(
        owner=user_db.email,
        code=otp_test_conf.code,
        session_id=otp_generate_session_id(),
        ttl=otp_test_conf.ttl,
    )
    await otp_auth_session.create(otp)

    user_data = UserAuthConfirmREQT(
        session_id=otp.session_id,
        otp=otp.code,
    )

    with pytest.raises(UserNotFoundERR):
        await user_authorization_usecase.register_confirm(user_data)