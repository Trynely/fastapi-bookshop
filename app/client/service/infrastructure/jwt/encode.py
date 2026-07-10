import jwt
from datetime import datetime, timedelta, timezone
from app.core.config.base import get_settings
from app.client.service.infrastructure.jwt.keys import load_private_key

settings = get_settings()

def jwt_encode(
    payload: dict,
    exp_timedelta: timedelta | None = None,
) -> str:
    to_encode = payload.copy()
    now = datetime.now(tz=timezone.utc)

    expire = (
        now + exp_timedelta
        if exp_timedelta
        else now + timedelta(minutes=settings.jwt.access_token_exp_minute)
    )

    to_encode.update(
        exp=int(expire.timestamp()),
        iat=int(now.timestamp()),
    )

    return jwt.encode(
        to_encode,
        load_private_key(),
        algorithm=settings.jwt.algorithm,
    )