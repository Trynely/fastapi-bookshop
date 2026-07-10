from app.client.db.postgres.models import ClientModel, OAuthProviderENUM

def user_make_is_google(user: ClientModel, oauth_id: str) -> None:
    user.oauth_provider = OAuthProviderENUM.GOOGLE
    user.oauth_id = oauth_id