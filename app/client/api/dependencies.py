import hmac
from dataclasses import asdict

from fastapi import Depends, Request, WebSocket, status
from jwt.exceptions import PyJWTError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.client.api.requests.user.auth import UserAuthorizedREQT
from app.client.exception.jwt.csrf import CsrfTokenInvalidERR
from app.client.exception.jwt.forbidden import JwtRoleForbiddenERR
from app.client.exception.jwt.invalid import JwtInvalidERR
from app.core.config.client.jwt.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.client.service.infrastructure.jwt.validate.is_valid_access import is_valid_jwt_access_token
from app.core.config.base import get_settings
from app.core.config.client.jwt.roles import AUTHORIZED_MANAGER, AUTHORIZED_USER
from app.core.config.shared.api.auth_headers import AUTHORIZATION_BEARER_FIELD_CONF, AUTHORIZATION_REQUEST_FIELD_CONF
from app.client.service.infrastructure.jwt.decode import jwt_decode

security = HTTPBearer(auto_error=False)

def auth_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserAuthorizedREQT:
    """Любой валидный access-токен, без учёта роли.

    Для витрины (корзина, заказы, отзывы, чат) использовать auth_client:
    менеджер — служебный аккаунт и покупателем быть не должен.
    """
    if not credentials:
        raise JwtInvalidERR()
    
    jwt_acces_token_payload = is_valid_jwt_access_token(credentials.credentials)
    return UserAuthorizedREQT.model_validate(asdict(jwt_acces_token_payload))


def require_roles(*allowed_roles: str):
    """Фабрика зависимостей: пускает только токены с ролью из allowed_roles."""
    def role_checker(
        user: UserAuthorizedREQT = Depends(auth_user),
    ) -> UserAuthorizedREQT:
        if user.role not in allowed_roles:
            raise JwtRoleForbiddenERR()
        return user

    return role_checker


auth_manager = require_roles(AUTHORIZED_MANAGER)
auth_client = require_roles(AUTHORIZED_USER)


def auth_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> UserAuthorizedREQT | None:
    """Опциональная авторизация покупателя.

    Менеджер здесь приравнивается к анониму: страницы отдаются, но события
    для персональных рекомендаций от служебного аккаунта не пишутся.
    """
    if credentials is None:
        return None

    jwt_access_token_payload = is_valid_jwt_access_token(
        credentials.credentials
    )

    user = UserAuthorizedREQT.model_validate(
        asdict(jwt_access_token_payload)
    )

    if user.role != AUTHORIZED_USER:
        return None

    return user
    

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
    

def csrf_protect(request: Request) -> None:
    """Double-submit cookie: заголовок X-CSRF-Token обязан совпадать с cookie.

    Защищает cookie-эндпоинты (refresh, logout), которые браузер вызывает
    по автоматически подставляемой refresh-cookie: кросс-сайт не сможет ни
    прочитать CSRF-cookie, ни выставить заголовок. Эндпоинты с Bearer-токеном
    в защите не нуждаются — заголовок Authorization кросс-сайт тоже не ставит.
    """
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    header_token = request.headers.get(CSRF_HEADER_NAME)

    if (
        not cookie_token
        or not header_token
        or not hmac.compare_digest(cookie_token, header_token)
    ):
        raise CsrfTokenInvalidERR()


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