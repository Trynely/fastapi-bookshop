import pytest
from app.client.api.requests.user.google_oauth import UserOauthREQT
from app.client.exception.user.oauth import GoogleAccountSecurityERR, OAuthProviderMismatchERR
from app.client.service.infrastructure.jwt.decode import jwt_decode
from app.client.db.postgres.models import OAuthProviderENUM
from app.core.config.client.test.dto import user_google_test_conf

@pytest.mark.asyncio
async def test_google_auth_create_new_user(
    user_google_authorization_usecase,
    user_repository,
    jwt_refresh_session,
    user_google_reqt,
):
    refresh_token = await user_google_authorization_usecase.authorize(user_google_reqt)

    payload = jwt_decode(refresh_token)

    user = await user_repository.get_by_email(user_google_reqt.email)

    assert user is not None
    assert user.oauth_provider == OAuthProviderENUM.GOOGLE
    assert user.oauth_id == user_google_reqt.oauth_id

    refresh_session_exists = await jwt_refresh_session.is_exists(payload.jti)

    assert refresh_session_exists is True


@pytest.mark.asyncio
async def test_google_auth_existing_google_user_success(
    user_google_authorization_usecase,
    google_user_db,
    jwt_refresh_session,
    user_google_reqt,
):
    refresh_token = await user_google_authorization_usecase.authorize(user_google_reqt)

    payload = jwt_decode(refresh_token)

    session_exists = await jwt_refresh_session.is_exists(payload.jti)

    assert session_exists is True


@pytest.mark.asyncio
async def test_google_auth_convert_local_user_to_google(
    user_google_authorization_usecase,
    user_db,
    user_repository,
):
    user_data = UserOauthREQT(
        email=user_db.email,
        username=user_db.username,
        oauth_id=user_google_test_conf.oauth_id,
    )

    await user_google_authorization_usecase.authorize(user_data)
    
    updated_user = await user_repository.get_by_email(user_data.email)
    assert updated_user.oauth_id == user_google_test_conf.oauth_id


@pytest.mark.asyncio
async def test_google_auth_invalid_oauth_id(
    user_google_authorization_usecase,
    google_user_db,
):
    user_data = UserOauthREQT(
        email=google_user_db.email,
        username=google_user_db.username,
        oauth_id="wrong-google-id",
    )

    with pytest.raises(GoogleAccountSecurityERR):
        await user_google_authorization_usecase.authorize(user_data)


@pytest.mark.asyncio
async def test_google_auth_provider_mismatch(
    user_google_authorization_usecase,
    github_user_db,
):
    user_data = UserOauthREQT(
        email=github_user_db.email,
        username=github_user_db.username,
        oauth_id=user_google_test_conf.oauth_id,
    )

    with pytest.raises(OAuthProviderMismatchERR):
        await user_google_authorization_usecase.authorize(user_data)