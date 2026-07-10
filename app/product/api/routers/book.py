from typing import List

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from app.client.api.dependencies import auth_user, auth_user_optional
from app.client.api.events.user.personal_reco import UserPersonalRecoEVENT
from app.client.api.requests.user.auth import UserAuthorizedREQT
from app.client.db.postgres.models import UserEventENUM
from app.client.service.infrastructure.rabbitmq.producer.reco_events import (
    publish_user_personal_books_reco_rmq,
    publish_user_personal_books_reco_rmq_safe,
)
from app.client.service.infrastructure.user.reco_profile import UserPersonalBooksRecoProfile
from app.product.api.events.book.personal_reco import BookPersonalRecoEVENT, SearchEventMeta
from app.product.api.requests.filter_by_category import (
    CategoryBooksByAuthorNameREQT,
    CategoryBooksByCountryREQT,
    CategoryBooksByTitleREQT,
)
from app.product.api.requests.filter_by_similar import FilterSimilarBooksREQT
from app.product.api.responses.book.main_reco import BooksMainRecoRESP
from app.product.api.responses.book.preview import BooksPreviewPaginationRESP
from app.product.api.responses.book.detail import BookDetailRESP
from app.product.service.infrastructure.query_handlers.book.detail import BookDetailQH
from app.product.service.infrastructure.query_handlers import CategoryBooksSearchQH
from app.product.service.infrastructure.query_handlers.book.filter import BookFilterQH
from app.product.service.infrastructure.query_handlers.book.main_reco import BooksMainRecommendationsQH
from app.product.service.infrastructure.query_handlers.book.similar import BookSimilarQH
from app.product.service.infrastructure.taskiq.tasks.book.qdrant_index import qdrant_index_books_task
from app.product.service.infrastructure.taskiq.tasks.book.update_popular_books import update_books_popularity
from app.shared.api.requests.cursor_pagintaion import (
    CursorEncodedPaginationREQT,
    CursorIDPaginationREQT,
    CursorMD5RandomPaginationREQT,
)

book_router = APIRouter(
    prefix="/books",
    tags=["📚 Книги"],
)

# home

@book_router.get(
    "/main/recommendations",
    summary="Главные Рекомендации",
    response_model=BooksMainRecoRESP,
)
@inject
async def get_main_book_recommendations(
    book_recommendations: FromDishka[BooksMainRecommendationsQH],
    user: UserAuthorizedREQT = Depends(auth_user),
    encoded_cursor: str | None = Query(None, max_length=512),
) -> BooksMainRecoRESP:
    page = await book_recommendations.for_user(
        user_id=user.sub,
        encoded_cursor=encoded_cursor,
    )

    return BooksMainRecoRESP.from_page(
        books=page.books,
        next_cursor=page.next_cursor,
    )


@book_router.get(
    "",
    summary="Список Книг По Фильтру",
    status_code=status.HTTP_200_OK,
)
@inject
async def filter_books_router(
    books_filter: FromDishka[BookFilterQH],
    id_cursor: CursorIDPaginationREQT = Depends(),
    encoded_cursor: CursorEncodedPaginationREQT = Depends(),
    by: str = Query(None, enum=["new", "popular"]),
) -> BooksPreviewPaginationRESP:
    if by == "new" and encoded_cursor.encoded_cursor is not None:
        raise HTTPException(
            status_code=400,
            detail="encoded cursor is not allowed for 'new'"
        )

    if by == "popular" and id_cursor.id_cursor is not None:
        raise HTTPException(
            status_code=400,
            detail="id cursor is not allowed for 'popular'"
        )
    
    if by == "new":
        return await books_filter.by_new(pagination=id_cursor)

    elif by == "popular":
        return await books_filter.by_popular(pagination=encoded_cursor)

# -------
# detail

@book_router.get(
    "/{book_slug}",
    response_model=BookDetailRESP,
    summary="Получить информацию о книге",
)
@inject
async def detail_book_router(
    book_slug: str,
    book: FromDishka[BookDetailQH],
    user: UserAuthorizedREQT | None = Depends(auth_user_optional),
) -> BookDetailRESP:
    book = await book.get_book(book_slug)

    if user:
        event = UserPersonalRecoEVENT(
            user_id=user.sub,
            type=UserEventENUM.VIEW,
            book_id=book.id,
        )

        await publish_user_personal_books_reco_rmq_safe(
            routing_key="events.view",
            event=event,
            correlation_id=str(user.sub),
        )

    return book


@book_router.get(
    "/{book_slug}/similar",
    summary="Похожие Книги По Категории И Автору",
    status_code=status.HTTP_200_OK,
)
@inject
async def similar_books_by_category_and_author_router(
    books_similar: FromDishka[BookSimilarQH],
    similar: FilterSimilarBooksREQT = Depends(),
    random_pagination: CursorMD5RandomPaginationREQT = Depends(),
) -> BooksPreviewPaginationRESP:
    return await books_similar.by_category_and_author(
        similar=similar,
        random_pagination=random_pagination,
    )

# -------
# books of category

@book_router.get(
    "/categories/{category_slug}",
    summary="Книги Категории", 
    status_code=status.HTTP_200_OK,
)
@inject
async def books_category_router(
    books_filter: FromDishka[BookFilterQH],
    category_slug: str,
    random_pagination: CursorMD5RandomPaginationREQT = Depends(),
) -> BooksPreviewPaginationRESP:
    return await books_filter.by_category(
        category_slug=category_slug,
        random_pagination=random_pagination,
    )


@book_router.get(
    "/categories/{category_slug}/author",
    summary="Книги Категории | Поиск По Имени Автора",
    status_code=status.HTTP_200_OK,
)
@inject
async def search_category_books_by_author_name_router(
    category_books_search: FromDishka[CategoryBooksSearchQH],
    filters: CategoryBooksByAuthorNameREQT = Depends(),
    pagination: CursorEncodedPaginationREQT = Depends(),
    user: UserAuthorizedREQT | None = Depends(auth_user_optional),
) -> BooksPreviewPaginationRESP:
    result = await category_books_search.by_author(
        filters=filters,
        pagination=pagination,
    )

    # Событие только на первой странице: листание — не новый поиск
    if user and pagination.encoded_cursor is None:
        event = UserPersonalRecoEVENT(
            user_id=user.sub,
            type=UserEventENUM.SEARCH,
            metadata=SearchEventMeta(
                query=filters.name,
                results_count=len(result.books),
            ).model_dump(),
        )

        await publish_user_personal_books_reco_rmq_safe(
            routing_key="events.search",
            event=event,
            correlation_id=str(user.sub),
        )

    return result


@book_router.get(
    "/categories/{category_slug}/title",
    summary="Книги Категории | Поиск По Названию Книги",
    status_code=status.HTTP_200_OK,
)
@inject
async def search_category_books_by_title_router(
    category_books_search: FromDishka[CategoryBooksSearchQH],
    filters: CategoryBooksByTitleREQT = Depends(),
    pagination: CursorEncodedPaginationREQT = Depends(),
    user: UserAuthorizedREQT | None = Depends(auth_user_optional),
) -> BooksPreviewPaginationRESP:
    result = await category_books_search.by_title(
        filters=filters,
        pagination=pagination,
    )

    # Событие только на первой странице: листание — не новый поиск
    if user and pagination.encoded_cursor is None:
        event = UserPersonalRecoEVENT(
            user_id=user.sub,
            type=UserEventENUM.SEARCH,
            metadata=SearchEventMeta(
                query=filters.title,
                results_count=len(result.books),
            ).model_dump(),
        )

        await publish_user_personal_books_reco_rmq_safe(
            routing_key="events.search",
            event=event,
            correlation_id=str(user.sub),
        )

    return result


@book_router.get(
    "/categories/{category_slug}/country",
    summary="Книги Категории | Поиск По Стране Производства", 
    status_code=status.HTTP_200_OK,
)
@inject
async def search_category_books_by_country_router(
    category_books_search: FromDishka[CategoryBooksSearchQH],
    filters: CategoryBooksByCountryREQT = Depends(),
    pagination: CursorEncodedPaginationREQT = Depends(),
) -> BooksPreviewPaginationRESP:
    return await category_books_search.by_country(
        filters=filters,
        pagination=pagination,
    )


@book_router.post(
    "/update-books-popularity/23edded/dwefewfew/dqwfqwfwqf",
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_update_books_popularity():
    """
    Запускает задачу пересчета популярности книг.
    Fire-and-forget вызов Taskiq.
    """

    await update_books_popularity.kiq()

    return {
        "status": "queued",
        "task": "update_books_popularity",
    }


@book_router.post(
    "/events/fdkhefkewqf/fdwowehfkwef/fwlkehfkwe",
    summary="TEST | Обработка События От Пользователя Для Персональной Рекомендации",
    status_code=status.HTTP_202_ACCEPTED,
)
async def handle_personalized_reco_event_router(
    event: BookPersonalRecoEVENT,
    user: UserAuthorizedREQT = Depends(auth_user),
):
    user_event = UserPersonalRecoEVENT(
        user_id=user.sub,
        **event.model_dump(),
    )

    await publish_user_personal_books_reco_rmq(
        routing_key=f"events.{event.type}",
        event=user_event,
        correlation_id=str(user.sub),
    )

    return {"status": "accepted"}


@book_router.post("/qdrant/index")
async def index_qdrant_books_collection():
    await qdrant_index_books_task.kiq()

    return {
        "status": "started"
    }