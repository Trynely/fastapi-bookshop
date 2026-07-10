from app.client.db.postgres.models import ClientModel, OAuthProviderENUM

def is_google_user(user: ClientModel) -> bool:
    return user.oauth_provider == OAuthProviderENUM.GOOGLE


def is_invalid_google_account(user: ClientModel, oauth_id: str) -> bool:
    return user.oauth_id != oauth_id