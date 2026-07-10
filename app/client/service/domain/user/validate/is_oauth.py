from app.client.db.postgres.models import ClientModel

def is_not_oauth_user(user: ClientModel) -> bool:
    return user.oauth_provider is None