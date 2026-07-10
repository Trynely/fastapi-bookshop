from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.shared.api.templates import templates

support_pages_router = APIRouter(include_in_schema=False)


@support_pages_router.get("/support", response_class=HTMLResponse)
async def support_chat_page(request: Request):
    """Чат поддержки (WebSocket)."""
    return templates.TemplateResponse(
        request=request,
        name="support/chat.html",
    )


@support_pages_router.get("/support/manager", response_class=HTMLResponse)
async def support_manager_page(request: Request):
    """Панель менеджера поддержки: очередь, активные и закрытые чаты."""
    return templates.TemplateResponse(
        request=request,
        name="support/manager.html",
    )
