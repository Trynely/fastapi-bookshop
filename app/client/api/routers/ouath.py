from dishka import FromDishka
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.client.api.requests.user.google_oauth import UserOauthREQT
from dishka.integrations.fastapi import inject
from app.client.api.cookies import set_auth_cookies
from app.client.exception.user.oauth import GoogleEmailNotVerifiedERR
from app.client.service.usecase.ouath.google_authorization import UserGoogleAuthorizationUC
from app.client.service.infrastructure.oauth.google.base import oauth
from app.core.config.client.oauth.google_request_callback import GOOGLE_REQUEST_CALLBACK_CONF
from app.core.config.client.oauth.google_scope import GOOGLE_SCOPE_CONF
from app.core.config.client.oauth.google_token_payload_fields import GOOGLE_TOKEN_EMAIL_VERIFIED_CONF, GOOGLE_TOKEN_USERINFO_CONF, GOOGLE_TOKEN_USERINFO_EMAIL_CONF, GOOGLE_TOKEN_USERINFO_OAUTH_ID_CONF, GOOGLE_TOKEN_USERINFO_USERNAME_CONF
from app.core.config.client.oauth.router_urls import GOOGLE_CALLBACK_URL_CONF, GOOGLE_LOGIN_URL_CONF, OAUTH_BASE_URL_CONF

oauth_router = APIRouter(
    prefix=OAUTH_BASE_URL_CONF,
    tags=["🔰 OAuth Авторизация"],
)

@oauth_router.get(
    GOOGLE_LOGIN_URL_CONF,
    summary="Войти Через Google",
)
async def google_login_router(request: Request):
    redirect_uri = request.url_for(GOOGLE_REQUEST_CALLBACK_CONF)

    return await oauth.google.authorize_redirect(
        request,
        redirect_uri,
        scope=GOOGLE_SCOPE_CONF,
    )


@oauth_router.get(
    GOOGLE_CALLBACK_URL_CONF,
    name=GOOGLE_REQUEST_CALLBACK_CONF,
)
@inject
async def google_callback_router(
    request: Request,
    google: FromDishka[UserGoogleAuthorizationUC],
):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token[GOOGLE_TOKEN_USERINFO_CONF]

    if not userinfo[GOOGLE_TOKEN_EMAIL_VERIFIED_CONF]:
        raise GoogleEmailNotVerifiedERR()

    user_data = UserOauthREQT(
        email=userinfo[GOOGLE_TOKEN_USERINFO_EMAIL_CONF],
        oauth_id=userinfo[GOOGLE_TOKEN_USERINFO_OAUTH_ID_CONF],
        username=userinfo[GOOGLE_TOKEN_USERINFO_USERNAME_CONF],
    )
    jwt_refresh_token = await google.authorize(user_data)

    response = RedirectResponse(url="/")
    set_auth_cookies(response, jwt_refresh_token)
    return response