from dataclasses import asdict

from fastapi import Depends, Request, WebSocket, status
from jwt.exceptions import PyJWTError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.client.api.requests.user.auth import UserAuthorizedREQT
from app.client.exception.jwt.invalid import JwtInvalidERR
from app.client.service.infrastructure.jwt.validate.is_valid_access import is_valid_jwt_access_token
from app.core.config.base import get_settings
from app.core.config.shared.api.auth_headers import AUTHORIZATION_BEARER_FIELD_CONF, AUTHORIZATION_REQUEST_FIELD_CONF
from app.client.service.infrastructure.jwt.decode import jwt_decode

security = HTTPBearer(auto_error=False)

def auth_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserAuthorizedREQT:
    if not credentials:
        raise JwtInvalidERR()
    
    jwt_acces_token_payload = is_valid_jwt_access_token(credentials.credentials)
    return UserAuthorizedREQT.model_validate(asdict(jwt_acces_token_payload))


def auth_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserAuthorizedREQT | None:
    if credentials is None:
        return None

    jwt_access_token_payload = is_valid_jwt_access_token(
        credentials.credentials
    )

    return UserAuthorizedREQT.model_validate(
        asdict(jwt_access_token_payload)
    )
    

async def auth_user_ws(websocket: WebSocket) -> UserAuthorizedREQT:
    auth_header = websocket.headers.get(AUTHORIZATION_REQUEST_FIELD_CONF)

    if auth_header and auth_header.startswith(f"{AUTHORIZATION_BEARER_FIELD_CONF} "):
        token = auth_header.removeprefix(f"{AUTHORIZATION_BEARER_FIELD_CONF} ").strip()
    else:
        # fallback для браузера: WebSocket API не позволяет ставить заголовки
        token = websocket.query_params.get("token")

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise RuntimeError("authorization header missing")

    try:
        return is_valid_jwt_access_token(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise
    

def get_jwt_refresh_cookie(request: Request) -> str:
    settings = get_settings()

    refresh_token = request.cookies.get(
        settings.jwt.refresh_token_field
    )

    if not refresh_token:
        raise JwtInvalidERR()

    try:
        payload = jwt_decode(refresh_token)
    except PyJWTError:
        raise JwtInvalidERR()

    if payload.type != settings.jwt.refresh_token_field:
        raise JwtInvalidERR()
    return refresh_token