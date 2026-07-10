from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.shared.api.templates import templates

order_pages_router = APIRouter(include_in_schema=False)


@order_pages_router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request):
    """Корзина пользователя."""
    return templates.TemplateResponse(
        request=request,
        name="order/cart.html",
    )


@order_pages_router.get("/wishlist", response_class=HTMLResponse)
async def wishlist_page(request: Request):
    """Избранные книги пользователя."""
    return templates.TemplateResponse(
        request=request,
        name="order/wishlist.html",
    )
