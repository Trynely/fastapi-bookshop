import pytest
from unittest.mock import patch
from starlette import status
from app.core.config.base import get_settings

settings = get_settings()

@pytest.mark.asyncio
@patch("app.user.usecases.authentication.send_otp_email.delay")
async def test_login_router_success(
    mock_send_email,
    async_client,
    user_login_reqt,
    user_db,
    clean_redis,
):
    response = await async_client.post(
    "/users/login",
    json={
        "email": user_login_reqt.email,
        "password": user_login_reqt.password,
    },
)

    print("STATUS:", response.status_code)
    print("BODY:", response.text)

    assert response.status_code == status.HTTP_200_OK
