from app.client.api.requests.user.auth import UserAuthConfirmREQT
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO
from app.client.dto.jwt.access import JWTAccessTokenDTO
from app.client.dto.jwt.pair import JWTTokensDTO
from app.client.dto.jwt.refresh import JWTRefreshTokenDTO
from app.client.exception.otp.invalid import OtpInvalidERR
from app.client.exception.otp import OtpExpiredERR
from app.client.exception.user.exists import UserNotFoundERR
from app.client.service.infrastructure.otp.validate.code_is_invalid import is_invalid_otp_code
from app.client.service.domain.user.validate.exists import is_user_not_found
from app.client.service.domain.user.validate.is_active import is_user_active
from app.client.service.infrastructure.jwt.refresh_session import JWTRefreshAuthSession
from app.client.service.infrastructure.otp.auth_session import OtpAuthSession
from app.core.config.base import Settings
from app.core.config.client.jwt.refresh_session_time import jwt_refresh_session_time_conf
from app.core.config.client.jwt.roles import AUTHORIZED_USER
from app.shared.service.infrastructure.base import is_exists
from app.client.service.infrastructure.jwt.decode import jwt_decode
from app.client.dto.otp.base import OtpDTO
from app.client.service.domain.user.activate import user_make_active
from app.client.service.infrastructure.jwt.generator import JWTGenerator
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction

class UserAuthorizationUC:
    def __init__(
        self,
        transaction: SQLAlchemyTransaction,
        user_repository: UserSQLAlchemyREPO,
        otp_auth_session: OtpAuthSession,
        jwt_refresh_session: JWTRefreshAuthSession,
        jwt_generator: JWTGenerator,
        settings: Settings,
    ):
        self._transaction = transaction
        self.user_repository = user_repository
        self.otp_auth_session = otp_auth_session
        self.jwt_refresh_session = jwt_refresh_session
        self.jwt_generator = jwt_generator
        self.settings = settings
        
    async def login_confirm(self, user_data: UserAuthConfirmREQT) -> JWTTokensDTO:
        otp = await self._get_valid_otp(user_data)

        user = await is_exists(
            self.user_repository.get_by_email_and_active(email=otp.owner),
            UserNotFoundERR(),
        )
        user_id = str(user.id)

        await self.otp_auth_session.delete(otp)
        return await self._jwt_tokens(user_id)
        
    async def register_confirm(self, user_data: UserAuthConfirmREQT) -> JWTTokensDTO:
        otp = await self._get_valid_otp(user_data)
        user = await self.user_repository.get_by_email(email=otp.owner)
        
        if is_user_not_found(user) or is_user_active(user):
            raise UserNotFoundERR()

        user_make_active(user)

        await self.user_repository.save(user)
        await self._transaction.commit()
        await self.otp_auth_session.delete(otp)

        user_id = str(user.id)
        return await self._jwt_tokens(user_id)
    
    async def _jwt_tokens(self, user_id: str) -> JWTTokensDTO:
        access_token_data = JWTAccessTokenDTO(
            sub=user_id,
            role=AUTHORIZED_USER,
        )
        access_token = self.jwt_generator.access_token(token_data=access_token_data)

        refresh_token_data = JWTRefreshTokenDTO(sub=user_id)
        refresh_token = self.jwt_generator.refresh_token(token_data=refresh_token_data)
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
    
    async def _get_valid_otp(self, user_data: UserAuthConfirmREQT) -> OtpDTO:
        otp = await is_exists(
            self.otp_auth_session.get(user_data.session_id), 
            OtpExpiredERR(),
        )

        if is_invalid_otp_code(otp, client_code=user_data.otp):
            raise OtpInvalidERR()
        return otp