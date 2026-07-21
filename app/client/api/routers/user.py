from datetime import time
from dishka import FromDishka
from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from app.client.api.dependencies import get_jwt_refresh_cookie
from app.client.api.requests.user.auth import UserAuthConfirmREQT
from app.client.api.requests.user.login import UserLoginREQT
from app.client.api.responses.jwt.access import JwtAccessTokenRESP
from app.client.api.requests.user.register import UserRegisterREQT
from dishka.integrations.fastapi import inject
from app.client.db.qdrant.collections.user_reco_profile import UserRecoProfileQdrantCollection
from app.client.service.usecase.user.authentication import UserAuthenticationUC
from app.client.service.usecase.user.authorization import UserAuthorizationUC
from app.client.service.usecase.user.logout import UserLogoutUC
from app.core.config.client.jwt.httponly_cookie import JWT_REFRESH_COOKIE_CONF
from app.client.api.responses.user.succes_otp_send import succes_otp_sending_to_email_resp
from app.core.config.client.user.router_urls import USER_BASE_URL_CONF, USER_LOGIN_URL_CONF, USER_LOGIN_VERIFY_URL_CONF, USER_LOGOUT_ALL_URL_CONF, USER_LOGOUT_URL_CONF, USER_REGISTER_URL_CONF, USER_REGISTER_VERIFY_URL_CONF

user_router = APIRouter(
    prefix=USER_BASE_URL_CONF,
    tags=["👨‍💻 Пользователи"],
)

@user_router.post(
    USER_REGISTER_URL_CONF,
    summary="Регистрация Пользователя",
    status_code=status.HTTP_201_CREATED,
)
@inject
async def register_user_router(
    user_data: UserRegisterREQT,
    user_authentication: FromDishka[UserAuthenticationUC],
):
    otp_session_id = await user_authentication.register(user_data)
    return succes_otp_sending_to_email_resp(otp_session_id)


@user_router.post(
    USER_LOGIN_URL_CONF,
    summary="Вход Пользователя",
    status_code=status.HTTP_200_OK,
)
@inject
async def login_user_router(
    user_data: UserLoginREQT,
    user_authentication: FromDishka[UserAuthenticationUC],
):
    otp_session_id = await user_authentication.login(user_data)
    return succes_otp_sending_to_email_resp(otp_session_id)


@user_router.post(
    USER_LOGIN_VERIFY_URL_CONF,
    summary="Подтвердить Вход",
    status_code=status.HTTP_200_OK,
)
@inject
async def user_login_confirm_router(
    user_data: UserAuthConfirmREQT,
    response: Response,
    user_authorization: FromDishka[UserAuthorizationUC],
):
    jwt = await user_authorization.login_confirm(
        user_data
    )
    
    response.set_cookie(**JWT_REFRESH_COOKIE_CONF, value=jwt.refresh_token)
    return JwtAccessTokenRESP(access_token=jwt.access_token)


@user_router.post(
    USER_REGISTER_VERIFY_URL_CONF,
    summary="Подтвердить Регистрацию",
    status_code=status.HTTP_200_OK,
)
@inject
async def user_register_confirm_router(
    user_data: UserAuthConfirmREQT,
    response: Response,
    user_authorization: FromDishka[UserAuthorizationUC],
):
    jwt = await user_authorization.register_confirm(
        user_data
    )

    response.set_cookie(**JWT_REFRESH_COOKIE_CONF, value=jwt.refresh_token)
    return JwtAccessTokenRESP(access_token=jwt.access_token)


@user_router.post(
    USER_LOGOUT_URL_CONF,
    summary="Выход Из Аккаунта",
    status_code=status.HTTP_204_NO_CONTENT,
)
@inject
async def user_logout_router(
    response: Response,
    user_logout: FromDishka[UserLogoutUC],
    refresh_token: str = Depends(get_jwt_refresh_cookie),
):
    await user_logout.from_device(refresh_token)
    
    response.delete_cookie(
        key=JWT_REFRESH_COOKIE_CONF["key"],
        path=JWT_REFRESH_COOKIE_CONF["path"],
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@user_router.post(
    USER_LOGOUT_ALL_URL_CONF,
    summary="Выход Со Всех Устройств",
    status_code=status.HTTP_204_NO_CONTENT,
)
@inject
async def user_logout_all_sessions_router(
    response: Response,
    user_logout: FromDishka[UserLogoutUC],
    refresh_token: str = Depends(get_jwt_refresh_cookie),
):
    await user_logout.from_all_devices(refresh_token)
    
    response.delete_cookie(
        key=JWT_REFRESH_COOKIE_CONF["key"],
        path=JWT_REFRESH_COOKIE_CONF["path"],
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@user_router.post("/qdrant/init/collection")
@inject
async def create_collect(user_reco_profile_qdrant_collection: FromDishka[UserRecoProfileQdrantCollection]):
    await user_reco_profile_qdrant_collection.init_collection()

    return {
        "status": "done"
    }