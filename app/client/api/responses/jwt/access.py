from pydantic import BaseModel
from app.core.config.shared.api.auth_headers import AUTHORIZATION_BEARER_FIELD_CONF

class JwtAccessTokenRESP(BaseModel):
    access_token: str
    token_type: str = AUTHORIZATION_BEARER_FIELD_CONF