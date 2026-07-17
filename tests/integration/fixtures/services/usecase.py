import pytest_asyncio
from app.client.service.usecase.jwt.refresh_update import JwtRefreshTokenUpdateUC
from app.client.service.usecase.ouath.google_authorization import UserGoogleAuthorizationUC
from app.client.service.usecase.user.authentication import UserAuthenticationUC
from app.client.service.usecase.user.authorization import UserAuthorizationUC
from app.client.service.usecase.user.logout import UserLogoutUC
from app.core.config.base import get_settings

# client
@pytest_asyncio.fixture(scope="function")
def user_authentication_usecase(
    transaction,
    user_repository,
    otp_auth_session,
):
    settings = get_settings()

    return UserAuthenticationUC(
        transaction=transaction,
        user_repository=user_repository,
        otp_auth_session=otp_auth_session,
        settings=settings,
    )


@pytest_asyncio.fixture(scope="function")
def user_authorization_usecase(
    transaction,
    user_repository,
    otp_auth_session,
    jwt_refresh_session,
    jwt_generator,
):
    settings = get_settings()

    return UserAuthorizationUC(
        transaction=transaction,
        user_repository=user_repository,
        otp_auth_session=otp_auth_session,
        jwt_refresh_session=jwt_refresh_session,
        jwt_generator=jwt_generator,
        settings=settings,
    )


@pytest_asyncio.fixture(scope="function")
def user_logout_usecase(
    jwt_refresh_session,
):
    return UserLogoutUC(
        jwt_refresh_session=jwt_refresh_session,
    )


@pytest_asyncio.fixture(scope="function")
def user_google_authorization_usecase(
    transaction,
    user_repository,
    jwt_generator,
    jwt_refresh_session,
):
    return UserGoogleAuthorizationUC(
        transaction=transaction,
        user_repository=user_repository,
        jwt_generator=jwt_generator,
        jwt_refresh_session=jwt_refresh_session,
    )


@pytest_asyncio.fixture(scope="function")
def jwt_refresh_update_usecase(
    jwt_refresh_session,
    jwt_generator,
    user_repository,
):
    return JwtRefreshTokenUpdateUC(
        jwt_refresh_session=jwt_refresh_session,
        jwt_generator=jwt_generator,
        user_repository=user_repository,
    )