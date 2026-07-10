from dishka import (
    Provider,
    provide,
    Scope,
)
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO
from app.client.db.postgres.repositories.sqlalchemy.user_event import UserEventSQLAlchemyREPO
from app.client.db.qdrant.collections.user_reco_profile import UserRecoProfileQdrantCollection
from app.client.service.infrastructure.jwt.refresh_session import JWTRefreshAuthSession
from app.client.service.infrastructure.otp.auth_session import OtpAuthSession
from app.client.db.qdrant.repositories.user.reco_profile import UserRecoProfileQdrantREPO
from app.client.service.infrastructure.taskiq.schedules.user.base import UserTaskiqSchedulesPublisher
from app.client.service.infrastructure.user.reco_profile import UserPersonalBooksRecoProfile, UserPersonalBooksRecoProfileCache, UserProfileUpdateProcess, UserRecoProfileEmbeddingTextBuilder
from app.client.service.usecase.jwt.refresh_update import JwtRefreshTokenUpdateUC
from app.client.service.usecase.user import UserAuthenticationUC, UserAuthorizationUC
from app.client.service.usecase.ouath.google_authorization import UserGoogleAuthorizationUC
from app.client.service.usecase.user.logout import UserLogoutUC
from app.core.config.base import Settings
from app.client.service.infrastructure.jwt.generator import JWTGenerator
from app.product.db.postgres.repositories.sqlalchemy.author import BookAuthorSQLAlchemyREPO
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.db.postgres.repositories.sqlalchemy.category import BookCategorySQLAlchemyREPO
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder
from app.shared.service.infrastructure.redis.clients import RedisClient

class ClientProvider(Provider):
    scope = Scope.REQUEST

    # ----
    #REPO

    @provide
    def user_alchemy_repo(
        self,
        session: AsyncSession,
    ) -> UserSQLAlchemyREPO:
        return UserSQLAlchemyREPO(session)
    
    @provide
    def user_event_alchemy_repo(
        self,
        session: AsyncSession,
    ) -> UserEventSQLAlchemyREPO:
        return UserEventSQLAlchemyREPO(session)
    
    # ----
    # UC
    
    @provide
    def user_authentication_uc(
        self,
        transaction: SQLAlchemyTransaction,
        user_repository: UserSQLAlchemyREPO,
        otp_auth_session: OtpAuthSession,
        settings: Settings,
    ) -> UserAuthenticationUC:
        return UserAuthenticationUC(
            transaction=transaction,
            user_repository=user_repository,
            otp_auth_session=otp_auth_session,
            settings=settings,
        )
    
    @provide
    def user_authorization_uc(
        self,
        transaction: SQLAlchemyTransaction,
        user_repository: UserSQLAlchemyREPO,
        otp_auth_session: OtpAuthSession,
        jwt_refresh_session: JWTRefreshAuthSession,
        jwt_generator: JWTGenerator,
        settings: Settings,
    ) -> UserAuthorizationUC:
        return UserAuthorizationUC(
            transaction=transaction,
            user_repository=user_repository,
            otp_auth_session=otp_auth_session,
            jwt_refresh_session=jwt_refresh_session,
            jwt_generator=jwt_generator,
            settings=settings,
        )
    
    @provide
    def user_google_authorization_uc(
        self,
        transaction: SQLAlchemyTransaction,
        user_repository: UserSQLAlchemyREPO,
        jwt_generator: JWTGenerator,
        jwt_refresh_session: JWTRefreshAuthSession,
    ) -> UserGoogleAuthorizationUC:
        return UserGoogleAuthorizationUC(
            transaction=transaction,
            user_repository=user_repository,
            jwt_generator=jwt_generator,
            jwt_refresh_session=jwt_refresh_session,
        )

    @provide
    def user_logout_uc(
        self,
        jwt_refresh_session: JWTRefreshAuthSession,
    ) -> UserLogoutUC:
        return UserLogoutUC(jwt_refresh_session=jwt_refresh_session)
    
    @provide
    def jwt_refresh_token_update_uc(
        self,
        jwt_refresh_session: JWTRefreshAuthSession,
        jwt_generator: JWTGenerator
    ) -> JwtRefreshTokenUpdateUC:
        return JwtRefreshTokenUpdateUC(
            jwt_generator=jwt_generator,
            jwt_refresh_session=jwt_refresh_session,
        )
    
    # ----
    # SERV
    
    @provide
    def jwt_generator(self) -> JWTGenerator:
        return JWTGenerator()
    
    @provide
    def jwt_refresh_auth_session(
        self,
        redis_connection: RedisClient,
    ) -> JWTRefreshAuthSession:
        return JWTRefreshAuthSession(redis_connection=redis_connection)
    
    @provide
    def otp_auth_session(
        self,
        redis_connection: RedisClient,
        settings: Settings,
    ) -> OtpAuthSession:
        return OtpAuthSession(
            redis=redis_connection,
            settings=settings,
        )
    
    @provide
    def user_personal_books_reco_profile_cache(
        self,
        redis: RedisClient,
    ) -> UserPersonalBooksRecoProfileCache:
        return UserPersonalBooksRecoProfileCache(redis=redis)
    
    @provide
    def user_reco_profile_qdrant_point_repo(
        self,
        qdrant_client: AsyncQdrantClient,
    ) -> UserRecoProfileQdrantREPO:
        return UserRecoProfileQdrantREPO(qdrant_client=qdrant_client)
    
    @provide
    def user_personal_books_reco_profile(
        self,
        embedder: OllamaEmbedder,
        user_profile_cache: UserPersonalBooksRecoProfileCache,
        user_event_repository: UserEventSQLAlchemyREPO,
        book_repository: BookSQLAlchemyREPO,
        book_author_repository: BookAuthorSQLAlchemyREPO,
        book_category_repository: BookCategorySQLAlchemyREPO,
        schedule_publisher: UserTaskiqSchedulesPublisher,
        user_reco_profile_qdrant_repo: UserRecoProfileQdrantREPO,
        books_qdrant_repo: BooksQdrantREPO,
        user_profile_update_locker: UserProfileUpdateProcess,
        user_reco_embed_text: UserRecoProfileEmbeddingTextBuilder,
    ) -> UserPersonalBooksRecoProfile:
        return UserPersonalBooksRecoProfile(
            embedder=embedder,
            schedule_publisher=schedule_publisher,
            user_profile_cache=user_profile_cache,
            user_event_repository = user_event_repository,
            book_repository = book_repository,
            book_author_repository = book_author_repository,
            book_category_repository = book_category_repository,
            user_reco_profile_qdrant_repo = user_reco_profile_qdrant_repo,
            books_qdrant_repo = books_qdrant_repo,
            user_profile_update_process = user_profile_update_locker,
            user_reco_embed_text=user_reco_embed_text,
        )
    
    @provide
    def user_profile_update_locker(
        self,
        redis: RedisClient,
    ) -> UserProfileUpdateProcess:
        return UserProfileUpdateProcess(redis=redis)
    
    @provide
    def user_profile_embed_text_builder(self) -> UserRecoProfileEmbeddingTextBuilder:
        return UserRecoProfileEmbeddingTextBuilder()
    
    @provide
    def user_taskiq_schedules_publisher(self) -> UserTaskiqSchedulesPublisher:
        return UserTaskiqSchedulesPublisher()
    
    @provide(scope=Scope.APP)
    def user_reco_profile_qdrant_collection(
        self,
        qdrant_client: AsyncQdrantClient,
    ) -> UserRecoProfileQdrantCollection:
        return UserRecoProfileQdrantCollection(qdrant_client=qdrant_client)