from dishka import FromDishka
from fastapi import APIRouter, Depends, Response, status
from app.client.api.cookies import clear_auth_cookies, set_auth_cookies
from app.client.api.dependencies import csrf_protect, get_jwt_refresh_cookie
from app.client.api.responses.jwt.access import JwtAccessTokenRESP
from dishka.integrations.fastapi import inject
from app.client.exception.jwt.replay_detected import JwtRefreshReplayDetectedERR
from app.client.service.usecase.jwt.refresh_update import JwtRefreshTokenUpdateUC
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
    _: None = Depends(csrf_protect),
):
    try:
        new_access_token, new_refresh_token = (
            await update_jwt_refresh.execute(refresh_token)
        )
    except JwtRefreshReplayDetectedERR:
        clear_auth_cookies(response)
        raise
    except Exception:
        clear_auth_cookies(response)
        raise

    set_auth_cookies(response, new_refresh_token)

    return JwtAccessTokenRESP(access_token=new_access_token)