from app.client.exception.jwt.invalid import JwtInvalidFormatERR
import jwt
from app.client.dto.user.authorized import UserAuthorizedDTO
from app.core.config.base import get_settings
from app.client.service.infrastructure.jwt.keys import load_public_key

settings = get_settings()

def jwt_decode(token: str) -> UserAuthorizedDTO:
    if "." not in token:
        raise JwtInvalidFormatERR()
    
    jwt_token_payload = jwt.decode(
        token,
        load_public_key(),
        algorithms=[settings.jwt.algorithm],
    )
    
    return UserAuthorizedDTO(**jwt_token_payload)