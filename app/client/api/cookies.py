import secrets

from fastapi import Response

from app.core.config.client.jwt.csrf import CSRF_COOKIE_CONF
from app.core.config.client.jwt.httponly_cookie import JWT_REFRESH_COOKIE_CONF


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_auth_cookies(response: Response, refresh_token: str) -> str:
    """Ставит httponly refresh-cookie и парный CSRF-cookie (double-submit).

    Вызывать везде, где выдаётся новый refresh-токен (вход, подтверждение
    регистрации, refresh, oauth), чтобы фронтенд всегда имел актуальный
    CSRF-токен для последующих cookie-эндпоинтов. Возвращает выданный токен.
    """
    response.set_cookie(**JWT_REFRESH_COOKIE_CONF, value=refresh_token)

    csrf_token = generate_csrf_token()
    response.set_cookie(**CSRF_COOKIE_CONF, value=csrf_token)

    return csrf_token


def clear_auth_cookies(response: Response) -> None:
    """Снимает refresh- и CSRF-cookie (logout, ротация при replay)."""
    response.delete_cookie(
        key=JWT_REFRESH_COOKIE_CONF["key"],
        path=JWT_REFRESH_COOKIE_CONF["path"],
    )
    response.delete_cookie(
        key=CSRF_COOKIE_CONF["key"],
        path=CSRF_COOKIE_CONF["path"],
    )
