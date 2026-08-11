from app.client.api.requests.user.google_oauth import UserOauthREQT
from app.client.db.postgres.models import ClientModel, OAuthProviderENUM
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO
from app.client.dto.jwt.refresh import JWTRefreshTokenDTO
from app.client.exception.user.oauth import OAuthProviderMismatchERR, GoogleAccountSecurityERR
from app.client.service.domain.user.validate.is_google import is_google_user, is_invalid_google_account
from app.client.service.domain.user.validate.exists import is_user_found
from app.client.service.domain.user.make_oauth import user_make_is_google
from app.client.service.domain.user.validate.is_oauth import is_not_oauth_user
from app.client.service.infrastructure.jwt.refresh_session import JWTRefreshAuthSession
from app.core.config.client.jwt.refresh_session_time import jwt_refresh_session_time_conf
from app.client.service.infrastructure.jwt.decode import jwt_decode
from app.client.service.infrastructure.jwt.generator import JWTGenerator
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction

class UserGoogleAuthorizationUC:
    def __init__(
        self,
        transaction: SQLAlchemyTransaction,
        user_repository: UserSQLAlchemyREPO,
        jwt_generator: JWTGenerator,
        jwt_refresh_session: JWTRefreshAuthSession,
    ):
        self._transaction = transaction
        self.user_repository = user_repository
        self.jwt_generator = jwt_generator
        self.jwt_refresh_session = jwt_refresh_session
        
    async def authorize(self, user_data: UserOauthREQT) -> str:
        user = await self.user_repository.get_by_email(user_data.email)

        if is_user_found(user):
            if is_google_user(user):
                if is_invalid_google_account(
                    user=user,
                    oauth_id=user_data.oauth_id,
                ):
                    raise GoogleAccountSecurityERR()
                
            elif is_not_oauth_user(user):
                user_make_is_google(
                    user=user,
                    oauth_id=user_data.oauth_id,
                )
                await self._transaction.commit()
            else:
                raise OAuthProviderMismatchERR()
        else:
            user = ClientModel(
                email=user_data.email,
                username=user_data.username,
                oauth_provider=OAuthProviderENUM.GOOGLE,
                oauth_id=user_data.oauth_id,
            )
            # save() использует session.merge() и возвращает сохранённый ORM-объект.
            # Именно у него после flush заполнен id; исходный transient-объект
            # остаётся с id=None и не должен использоваться для JWT subject.
            user = await self.user_repository.save(user)
            await self._transaction.commit()

        user_id = str(user.id)
        
        refresh_token_data = JWTRefreshTokenDTO(sub=user_id)
        refresh_token = self.jwt_generator.refresh_token(token_data=refresh_token_data)
        refresh_token_payload = jwt_decode(refresh_token)

        await self.jwt_refresh_session.create(
            user_id=user_id,
            jti=refresh_token_payload.jti,
            ttl=jwt_refresh_session_time_conf(),
        )

        return refresh_token
