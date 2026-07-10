from dataclasses import dataclass

from app.client.db.postgres.models import OAuthProviderENUM

@dataclass(frozen=True, slots=True)
class UserTestConf:
    email: str = "test@example.com"
    username: str = "Test"
    password: str = "Hashedpassword12345&"
    is_active: bool = True

user_test_conf = UserTestConf()


@dataclass(frozen=True, slots=True)
class UserGoogleTestConf:
    email: str = "testgoogle@example.com"
    username: str = "Test Google"
    password: str | None = None
    oauth_provider: OAuthProviderENUM = OAuthProviderENUM.GOOGLE
    oauth_id: str = "google-test-oauth-id-123"
    is_active: bool = True

user_google_test_conf = UserGoogleTestConf()


@dataclass(frozen=True, slots=True)
class UserGithubTestConf:
    email: str = "testgithub@example.com"
    username: str = "Test Github"
    password: str | None = None
    oauth_provider: OAuthProviderENUM = OAuthProviderENUM.GITHUB
    oauth_id: str = "github-test-oauth-id-123"
    is_active: bool = True

user_github_test_conf = UserGithubTestConf()