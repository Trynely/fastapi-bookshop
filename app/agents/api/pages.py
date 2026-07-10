from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.shared.api.templates import templates

agent_pages_router = APIRouter(include_in_schema=False)


@agent_pages_router.get("/agent", response_class=HTMLResponse)
async def agent_chat_page(request: Request):
    """Чат с ИИ консультантом (SSE)."""
    return templates.TemplateResponse(
        request=request,
        name="agents/chat.html",
    )
