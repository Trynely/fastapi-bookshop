from app.core.config.client.jwt.httponly_cookie import (
    JWT_REFRESH_COOKIE_LIFETIME_CONF,
)

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

# double-submit cookie: НЕ httponly — фронтенд читает значение cookie и эхом
# кладёт его в заголовок X-CSRF-Token. Секретность токена не требуется:
# защита в том, что кросс-сайт не может ни прочитать cookie, ни выставить
# кастомный заголовок (CORS этого не позволяет).
CSRF_COOKIE_CONF = {
    "key": CSRF_COOKIE_NAME,
    "httponly": False,
    "secure": False,
    "samesite": "lax",
    # path "/" — cookie доступен JS витрины и панели менеджера
    "path": "/",
    "max_age": JWT_REFRESH_COOKIE_LIFETIME_CONF,
}
