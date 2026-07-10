from app.client.db.postgres.models import ClientModel

def is_user_active(user: ClientModel) -> bool:
    return user.is_active


def is_user_not_active(user: ClientModel) -> bool:
    return not user.is_active