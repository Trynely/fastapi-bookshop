from app.client.dto.jwt.access import JWTAccessTokenDTO
from app.client.dto.jwt.pair import JWTTokensDTO
from app.client.dto.jwt.refresh import JWTRefreshTokenDTO
from app.client.exception.user.invalid_creds import UserInvalidCredentialsERR
from app.client.service.infrastructure.jwt.decode import jwt_decode
from app.client.service.infrastructure.jwt.generator import JWTGenerator
from app.client.service.infrastructure.jwt.refresh_session import JWTRefreshAuthSession
from app.client.service.infrastructure.user.check_password import user_check_password
from app.core.config.client.jwt.refresh_session_time import jwt_refresh_session_time_conf
from app.core.config.client.jwt.roles import AUTHORIZED_MANAGER
from app.support.api.requests.manager_login import ManagerLoginREQT
from app.support.db.sqlalchemy.repositories.manager import ManagerSQLAlchemyRepository


class ManagerLoginUC:
    """Вход менеджера с панели поддержки: без OTP, только для роли manager."""

    def __init__(
        self,
        manager_repository: ManagerSQLAlchemyRepository,
        jwt_refresh_session: JWTRefreshAuthSession,
        jwt_generator: JWTGenerator,
    ):
        self.manager_repository = manager_repository
        self.jwt_refresh_session = jwt_refresh_session
        self.jwt_generator = jwt_generator

    async def execute(self, login_data: ManagerLoginREQT) -> JWTTokensDTO:
        manager = await self.manager_repository.get_by_email(email=login_data.email)

        if manager is None or not manager.is_active or not manager.password:
            raise UserInvalidCredentialsERR()

        try:
            password_valid = user_check_password(
                client_password=login_data.password,
                hashed_password=manager.password,
            )
        except ValueError:
            # в БД лежит не bcrypt-хэш — считаем креды невалидными
            password_valid = False

        if not password_valid:
            raise UserInvalidCredentialsERR()

        user_id = str(manager.id)

        access_token = self.jwt_generator.access_token(
            JWTAccessTokenDTO(sub=user_id, role=AUTHORIZED_MANAGER)
        )

        refresh_token = self.jwt_generator.refresh_token(
            JWTRefreshTokenDTO(sub=user_id)
        )
        refresh_token_payload = jwt_decode(refresh_token)

        await self.jwt_refresh_session.create(
            user_id=user_id,
            jti=refresh_token_payload.jti,
            ttl=jwt_refresh_session_time_conf(),
        )

        return JWTTokensDTO(
            access_token=access_token,
            refresh_token=refresh_token,
        )
