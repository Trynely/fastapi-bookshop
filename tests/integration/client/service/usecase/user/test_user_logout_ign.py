import pytest
from unittest.mock import patch
from app.core.config.base import get_settings
from app.core.config.client.jwt.refresh_session_time import jwt_refresh_session_time_conf

@pytest.mark.asyncio
@patch("app.client.service.usecase.user.logout.jwt_decode")
async def test_user_logout_from_device_success(
    mock_jwt_decode,
    user_logout_usecase,
    jwt_refresh_session,
):
    settings = get_settings()
    user_id = 1
    jti = "test_jti"

    mock_jwt_decode.return_value = type(
        "Payload",
        (),
        {
            "sub": user_id,
            "jti": jti,
        },
    )()

    await jwt_refresh_session.create(
        user_id=user_id,
        jti=jti,
        ttl=jwt_refresh_session_time_conf(),
    )
    assert await jwt_refresh_session.is_exists(jti)

    await user_logout_usecase.from_device("refresh_token")

    assert not await jwt_refresh_session.is_exists(jti)


@pytest.mark.asyncio
@patch("app.client.service.usecase.user.logout.jwt_decode")
async def test_user_logout_from_all_devices_success(
    mock_jwt_decode,
    user_logout_usecase,
    jwt_refresh_session,
):
    settings = get_settings()
    user_id = 1
    jti_1 = "jti_1"
    jti_2 = "jti_2"

    mock_jwt_decode.return_value = type(
        "Payload",
        (),
        {
            "sub": user_id,
            "jti": None,
        },
    )()

    await jwt_refresh_session.create(
        user_id=user_id,
        jti=jti_1,
        ttl=jwt_refresh_session_time_conf(),
    )
    await jwt_refresh_session.create(
        user_id=user_id,
        jti=jti_2,
        ttl=jwt_refresh_session_time_conf(),
    )

    assert await jwt_refresh_session.is_exists(jti_1)
    assert await jwt_refresh_session.is_exists(jti_2)

    await user_logout_usecase.from_all_devices("refresh_token")

    assert not await jwt_refresh_session.is_exists(jti_1)
    assert not await jwt_refresh_session.is_exists(jti_2)