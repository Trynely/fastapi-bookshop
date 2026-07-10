from app.client.dto.jwt.access import JWTAccessTokenDTO
from app.client.dto.jwt.refresh import JWTRefreshTokenDTO
from app.client.exception.jwt.replay_detected import JwtRefreshReplayDetectedERR
from app.client.service.infrastructure.jwt.refresh_session import JWTRefreshAuthSession
from app.core.config.client.jwt.refresh_session_time import jwt_refresh_session_time_conf
from app.core.config.client.jwt.roles import AUTHORIZED_USER
from app.client.service.infrastructure.jwt.decode import jwt_decode
from app.client.service.infrastructure.jwt.generator import JWTGenerator

class JwtRefreshTokenUpdateUC:
    def __init__(
        self,
        jwt_refresh_session: JWTRefreshAuthSession,
        jwt_generator: JWTGenerator,
    ):
        self.jwt_generator = jwt_generator
        self.jwt_refresh_session = jwt_refresh_session

    def _refresh_token_payload(self, refresh_token: str) -> tuple:
        payload = jwt_decode(refresh_token)
        
        user_id = payload.sub
        jti = payload.jti

        return user_id, jti

    async def execute(self, refresh_token: str) -> tuple:
        user_id, jti = self._refresh_token_payload(refresh_token)
        refresh_is_exists = await self.jwt_refresh_session.is_exists(jti)

        if not refresh_is_exists:
            await self.jwt_refresh_session.remove_all_user_sessions(user_id)
            raise JwtRefreshReplayDetectedERR()

        await self.jwt_refresh_session.remove(
            user_id=user_id,
            jti=jti,
        )

        new_refresh = self.jwt_generator.refresh_token(
            JWTRefreshTokenDTO(sub=user_id)
        )
        new_refresh_payload = jwt_decode(new_refresh)

        await self.jwt_refresh_session.create(
            user_id=user_id,
            jti=new_refresh_payload.jti,
            ttl=jwt_refresh_session_time_conf(),
        )

        new_access = self.jwt_generator.access_token(
            JWTAccessTokenDTO(
                sub=user_id,
                role=AUTHORIZED_USER,
            )
        )

        return new_access, new_refresh