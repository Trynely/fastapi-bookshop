import pytest
from app.client.dto.jwt.refresh import JWTRefreshTokenDTO
from app.client.exception.jwt.replay_detected import JwtRefreshReplayDetectedERR
from app.core.config.base import get_settings
from app.core.config.client.jwt.refresh_session_time import jwt_refresh_session_time_conf
from app.client.service.infrastructure.jwt.decode import jwt_decode

settings = get_settings()

@pytest.mark.asyncio
async def test_jwt_refresh_update_success(
    jwt_refresh_update_usecase,
    jwt_generator,
    jwt_refresh_session,
    clean_redis,
):
    user_id = "1"

    refresh = jwt_generator.refresh_token(
        JWTRefreshTokenDTO(sub=user_id)
    )

    payload = jwt_decode(refresh)

    await jwt_refresh_session.create(
        user_id=user_id,
        jti=payload.jti,
        ttl=jwt_refresh_session_time_conf(),
    )

    new_access, new_refresh = await jwt_refresh_update_usecase.execute(
        refresh
    )

    assert new_access
    assert new_refresh
    assert new_access != refresh


@pytest.mark.asyncio
async def test_jwt_refresh_update_replay_attack(
    jwt_refresh_update_usecase,
    jwt_generator,
    clean_redis,
):
    user_id = "1"

    refresh = jwt_generator.refresh_token(
        JWTRefreshTokenDTO(sub=user_id)
    )

    with pytest.raises(JwtRefreshReplayDetectedERR):
        await jwt_refresh_update_usecase.execute(refresh)


@pytest.mark.asyncio
async def test_old_jwt_refresh_removed_after_rotation(
    jwt_refresh_update_usecase,
    jwt_generator,
    jwt_refresh_session,
):
    user_id = "1"

    refresh = jwt_generator.refresh_token(
        JWTRefreshTokenDTO(sub=user_id)
    )

    payload = jwt_decode(refresh)

    await jwt_refresh_session.create(
        user_id=user_id,
        jti=payload.jti,
        ttl=jwt_refresh_session_time_conf(),
    )

    await jwt_refresh_update_usecase.execute(refresh)
    exists = await jwt_refresh_session.is_exists(payload.jti)
    assert exists is False


@pytest.mark.asyncio
async def test_jwt_new_refresh_saved_in_session(
    jwt_refresh_update_usecase,
    jwt_generator,
    jwt_refresh_session,
):
    user_id = "1"

    refresh = jwt_generator.refresh_token(
        JWTRefreshTokenDTO(sub=user_id)
    )

    payload = jwt_decode(refresh)

    await jwt_refresh_session.create(
        user_id=user_id,
        jti=payload.jti,
        ttl=jwt_refresh_session_time_conf(),
    )

    _, new_refresh = await jwt_refresh_update_usecase.execute(
        refresh
    )

    new_payload = jwt_decode(new_refresh)

    exists = await jwt_refresh_session.is_exists(
        new_payload.jti
    )
    assert exists is True