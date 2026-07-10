from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.shared.api.templates import templates

product_pages_router = APIRouter(include_in_schema=False)


@product_pages_router.get("/books", response_class=HTMLResponse)
async def books_catalog_page(request: Request):
    """Каталог книг: фильтр new/popular + cursor-пагинация."""
    return templates.TemplateResponse(
        request=request,
        name="product/catalog.html",
    )


@product_pages_router.get("/books/{book_slug}", response_class=HTMLResponse)
async def book_detail_page(request: Request, book_slug: str):
    """Карточка книги: детали, похожие книги, отзывы (offset-пагинация)."""
    return templates.TemplateResponse(
        request=request,
        name="product/detail.html",
        context={"book_slug": book_slug},
    )


@product_pages_router.get("/categories/{category_slug}", response_class=HTMLResponse)
async def category_books_page(request: Request, category_slug: str):
    """Книги категории: поиск по автору/названию/стране + cursor-пагинация."""
    return templates.TemplateResponse(
        request=request,
        name="product/category.html",
        context={"category_slug": category_slug},
    )
