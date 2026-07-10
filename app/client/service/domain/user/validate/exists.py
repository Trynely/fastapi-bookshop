from app.client.db.postgres.models import ClientModel

def is_user_found(user: ClientModel) -> bool:
    return user is not None


def is_user_not_found(user: ClientModel) -> bool:
    return user is None