from app.client.db.postgres.models import ClientModel

def user_update_credentials(
    user: ClientModel,
    password: str,
    username: str,
    user_role: str,
) -> None:
    user.password = password
    user.username = username
    user.role = user_role