import bcrypt
from app.shared.service.infrastructure.base import str_to_bytes

def user_hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashed.decode("utf-8")


def user_check_password(
    client_password: str,
    hashed_password: str
) -> bool:
    return bcrypt.checkpw(
        password=client_password.encode(),
        hashed_password=str_to_bytes(hashed_password)
    )