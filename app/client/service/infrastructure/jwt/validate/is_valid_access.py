from jwt.exceptions import PyJWTError
from app.client.dto.user.authorized import UserAuthorizedDTO
from app.client.exception.jwt.invalid import JwtInvalidERR, JwtTypeInvalidERR
from app.client.service.infrastructure.jwt.decode import jwt_decode
from app.core.config.base import get_settings

def is_valid_jwt_access_token(token: str) -> UserAuthorizedDTO:
    settings = get_settings()

    try:
        acces_token_payload = jwt_decode(token)
    except PyJWTError:
        raise JwtInvalidERR()

    if acces_token_payload.type != settings.jwt.access_token_field:
        raise JwtTypeInvalidERR()
    return acces_token_payload