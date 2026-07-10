import pytest
from app.client.dto.jwt.refresh import JWTRefreshTokenDTO
from app.core.config.base import get_settings
from app.core.config.client.jwt.refresh_session_time import jwt_refresh_session_time_conf
from app.client.service.infrastructure.jwt.decode import jwt_decode

settings = get_settings()

@pytest.mark.asyncio
async def test_refresh_sessions_limit_removes_oldest(
    jwt_generator,
    jwt_refresh_session,
):
    user_id = "1"

    max_sessions = settings.auth.max_auth_user_sessions
    refresh_tokens = []

    for _ in range(max_sessions):
        refresh = jwt_generator.refresh_token(
            JWTRefreshTokenDTO(sub=user_id)
        )

        payload = jwt_decode(refresh)

        await jwt_refresh_session.create(
            user_id=user_id,
            jti=payload.jti,
            ttl=jwt_refresh_session_time_conf(),
        )

        refresh_tokens.append(payload.jti)

    oldest_jti = refresh_tokens[0]

    new_refresh = jwt_generator.refresh_token(
        JWTRefreshTokenDTO(sub=user_id)
    )
    new_payload = jwt_decode(new_refresh)
    
    await jwt_refresh_session.create(
        user_id=user_id,
        jti=new_payload.jti,
        ttl=jwt_refresh_session_time_conf(),
    )

    exists = await jwt_refresh_session.is_exists(oldest_jti)
    assert exists is False