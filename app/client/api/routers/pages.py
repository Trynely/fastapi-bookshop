from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.shared.api.templates import templates

client_pages_router = APIRouter(include_in_schema=False)


@client_pages_router.get("/auth", response_class=HTMLResponse)
async def auth_page(request: Request):
    """Вход / регистрация с подтверждением по OTP."""
    return templates.TemplateResponse(
        request=request,
        name="client/auth.html",
    )
