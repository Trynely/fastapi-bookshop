from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO
from app.client.dto.jwt.access import JWTAccessTokenDTO
from app.client.dto.jwt.refresh import JWTRefreshTokenDTO
from app.client.exception.jwt.invalid import JwtInvalidERR
from app.client.exception.jwt.replay_detected import JwtRefreshReplayDetectedERR
from app.client.service.infrastructure.jwt.refresh_session import JWTRefreshAuthSession
from app.core.config.client.jwt.refresh_session_time import jwt_refresh_session_time_conf
from app.core.config.client.jwt.roles import client_role_to_jwt_role
from app.client.service.infrastructure.jwt.decode import jwt_decode
from app.client.service.infrastructure.jwt.generator import JWTGenerator

class JwtRefreshTokenUpdateUC:
    def __init__(
        self,
        jwt_refresh_session: JWTRefreshAuthSession,
        jwt_generator: JWTGenerator,
        user_repository: UserSQLAlchemyREPO,
    ):
        self.jwt_generator = jwt_generator
        self.jwt_refresh_session = jwt_refresh_session
        self.user_repository = user_repository

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

        # роль не хранится в refresh-токене: берём актуальную из БД,
        # чтобы менеджер не терял роль, а деактивированный аккаунт — не продлевался
        user = await self.user_repository.get_by_id(int(user_id))

        if user is None or not user.is_active:
            await self.jwt_refresh_session.remove_all_user_sessions(user_id)
            raise JwtInvalidERR()

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
                role=client_role_to_jwt_role(user.role),
            )
        )

        return new_access, new_refresh
