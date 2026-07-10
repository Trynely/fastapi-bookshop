import pytest
from app.client.api.requests.user.google_oauth import UserOauthREQT
from app.client.api.requests.user.login import UserLoginREQT
from app.client.api.requests.user.register import UserRegisterREQT
from app.core.config.client.test.dto import user_test_conf, user_google_test_conf

# client
@pytest.fixture
def user_login_reqt():
    return UserLoginREQT(
        email=user_test_conf.email,
        password=user_test_conf.password,
    )


@pytest.fixture
def user_register_reqt():
    return UserRegisterREQT(
        email=user_test_conf.email,
        username=user_test_conf.username,
        password=user_test_conf.password,
    )


@pytest.fixture
def user_google_reqt():
    return UserOauthREQT(
        email=user_google_test_conf.email,
        username=user_google_test_conf.username,
        oauth_id=user_google_test_conf.oauth_id,
    )