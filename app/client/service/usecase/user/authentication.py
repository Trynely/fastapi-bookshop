import uuid
from app.client.service.infrastructure.otp.generate import generate_otp
from app.client.service.infrastructure.otp.validate.exist import is_otp_not_expired
from app.client.service.domain.user.validate.is_google import is_google_user
from app.client.service.infrastructure.otp.auth_session import OtpAuthSession, otp_generate_session_id
from app.client.service.infrastructure.user.check_password import user_hash_password, user_check_password
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO
from app.client.exception.otp.expire import OtpNotExpiredERR
from app.client.exception.user.exists import UserAlreadyExistsERR
from app.client.exception.user.invalid_creds import UserInvalidCredentialsERR
from app.client.service.infrastructure.taskiq.tasks.otp.send_otp_to_email import send_otp_email
from app.client.service.domain.user.validate.exists import is_user_found, is_user_not_found
from app.client.service.domain.user.validate.is_active import is_user_active
from app.client.service.domain.user.update_creds import user_update_credentials
from app.core.config.base import Settings
from app.client.api.requests.user.login import UserLoginREQT
from app.client.api.requests.user.register import UserRegisterREQT
from app.client.db.postgres.models import ClientModel, ClientRoleENUM
from app.client.dto.otp.base import OtpDTO
from app.shared.service.infrastructure.base import is_exists

class UserAuthenticationUC:
    def __init__(
        self,
        transaction: SQLAlchemyTransaction,
        user_repository: UserSQLAlchemyREPO,
        otp_auth_session: OtpAuthSession,
        settings: Settings,
    ):
        self._transaction = transaction
        self.user_repository = user_repository
        self.otp_auth_session = otp_auth_session
        self.settings = settings
        
    async def login(self, user_data: UserLoginREQT) -> uuid.UUID:
        user = await is_exists(
            self.user_repository.get_by_email_and_active(email=user_data.email),
            UserInvalidCredentialsERR(),
        )

        if is_google_user(user) or not user_check_password(
            client_password=user_data.password,
            hashed_password=user.password,
        ):
            raise UserInvalidCredentialsERR()
        
        otp = await self.otp_auth_session.get_by_owner(owner=user_data.email)
        
        if is_otp_not_expired(otp):
            raise OtpNotExpiredERR()
        
        otp_session_id = otp_generate_session_id()
        new_otp = OtpDTO(
            owner=user_data.email,
            code=generate_otp(),
            session_id=otp_session_id,
            ttl=self.settings.otp.ttl,
        )
        await self.otp_auth_session.create(new_otp)
        
        await send_otp_email.kiq(user_data.email, new_otp.code)
        return otp_session_id

    async def register(
        self,
        user_data: UserRegisterREQT,
    ) -> uuid.UUID:
        user = await self.user_repository.get_by_email(email=user_data.email)
        user_role = ClientRoleENUM.USER

        if is_user_found(user) and is_user_active(user):
            raise UserAlreadyExistsERR()
        
        otp = await self.otp_auth_session.get_by_owner(owner=user_data.email)
        
        if is_otp_not_expired(otp):
            raise OtpNotExpiredERR()

        if is_user_not_found(user):
            user = ClientModel(
                email=user_data.email,
                username=user_data.username,
                password=user_hash_password(user_data.password),
                role=user_role,
                is_active=False,
            )
        else:
            user_update_credentials(
                user=user,
                password=user_hash_password(user_data.password),
                username=user_data.username,
                user_role=user_role,
            )

        await self.user_repository.save(user)
        await self._transaction.commit()

        otp_session_id = otp_generate_session_id()
        new_otp = OtpDTO(
            owner=user_data.email,
            code=generate_otp(),
            session_id=otp_session_id,
            ttl=self.settings.otp.ttl,
        )
        await self.otp_auth_session.create(new_otp)
        
        await send_otp_email.kiq(user_data.email, new_otp.code)
        return otp_session_id