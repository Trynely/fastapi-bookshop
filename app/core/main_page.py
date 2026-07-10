from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.shared.api.templates import templates

template_router = APIRouter(include_in_schema=False)


@template_router.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )
