from app.core.config.base import get_settings

settings = get_settings()

JWT_ACCESS_COOKIE_LIFETIME_CONF = 60 * settings.jwt.access_token_exp_minute
JWT_REFRESH_COOKIE_LIFETIME_CONF = 60 * 60 * 24 * settings.jwt.refresh_token_exp_days

JWT_ACCESS_COOKIE_CONF = {
    "key": settings.jwt.access_token_field,
    "httponly": True,
    "secure": False,
    "samesite": "lax",
    "path": "/",
    "max_age": JWT_ACCESS_COOKIE_LIFETIME_CONF, # 10 min
}

JWT_REFRESH_COOKIE_CONF = {
    "key": settings.jwt.refresh_token_field,
    "httponly": True,
    "secure": False,
    "samesite": "strict",
    "path": "/api/users/",
    "max_age": JWT_REFRESH_COOKIE_LIFETIME_CONF, # 7 days
}