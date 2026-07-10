from dishka import FromDishka
from fastapi import APIRouter, Depends, Response, status
from app.client.api.dependencies import get_jwt_refresh_cookie
from app.client.api.responses.jwt.access import JwtAccessTokenRESP
from dishka.integrations.fastapi import inject
from app.client.exception.jwt.replay_detected import JwtRefreshReplayDetectedERR
from app.client.service.usecase.jwt.refresh_update import JwtRefreshTokenUpdateUC
from app.core.config.client.jwt.httponly_cookie import JWT_REFRESH_COOKIE_CONF
from app.core.config.base import get_settings
from app.core.config.client.jwt.router_urls import JWT_BASE_URL_CONF, JWT_REFRESH_URL_CONF

jwt_router = APIRouter(
    prefix=JWT_BASE_URL_CONF,
    tags=["🔰 JWT Токены"],
)

@jwt_router.post(
    JWT_REFRESH_URL_CONF,
    summary="Обновить Refresh Токен",
    status_code=status.HTTP_200_OK,
)
@inject
async def update_refresh_token_router(
    response: Response,
    update_jwt_refresh: FromDishka[JwtRefreshTokenUpdateUC],
    refresh_token: str = Depends(get_jwt_refresh_cookie),
):
    settings = get_settings()

    try:
        new_access_token, new_refresh_token = (
            await update_jwt_refresh.execute(refresh_token)
        )
    except JwtRefreshReplayDetectedERR:
        response.delete_cookie(settings.jwt.refresh_token_field)
        raise
    except Exception:
        response.delete_cookie(settings.jwt.refresh_token_field)
        raise

    response.set_cookie(
        **JWT_REFRESH_COOKIE_CONF,
        value=new_refresh_token,
    )

    return JwtAccessTokenRESP(access_token=new_access_token)