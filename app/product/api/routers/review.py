from dishka import FromDishka
from fastapi import (
    APIRouter,
    Depends,
    status,
)
from app.client.api.events.user.personal_reco import UserPersonalRecoEVENT
from app.client.api.requests.user.auth import UserAuthorizedREQT
from app.client.db.postgres.models import UserEventENUM
from app.client.service.infrastructure.rabbitmq.producer.reco_events import publish_user_personal_books_reco_rmq_safe
from app.product.api.events.book.personal_reco import RatingEventMeta
from app.product.api.requests.review.write import ReviewWriteREQT
from app.product.api.responses.review.preview import ReviewsPreviewPaginationRESP
from app.product.service.infrastructure.query_handlers.review.filter import BookReviewFilterQH
from app.product.service.usecase.review.write import WriteReview
from app.shared.api.requests.offset_pagination import OffsetPagination
from app.client.api.dependencies import auth_user
from dishka.integrations.fastapi import inject

book_review_router = APIRouter(prefix="/reviews", tags=["⭐ Отзывы Книг"])

@book_review_router.get(
    "/{book_slug}",
    summary="Отзывы по Книге",
    status_code=status.HTTP_200_OK,
)
@inject
async def reviews_by_book_router(
    book_slug: str,
    query_handler: FromDishka[BookReviewFilterQH],
    pagination: OffsetPagination = Depends(),
) -> ReviewsPreviewPaginationRESP:
    return await query_handler.get_reviews_by_book(
        book_slug=book_slug,
        pagination=pagination,
    )


@book_review_router.post(
    "",
    summary="Написать Отзыв",
    status_code=status.HTTP_201_CREATED,
)
@inject
async def write_review_router(
    review_data: ReviewWriteREQT,
    write_review: FromDishka[WriteReview],
    user: UserAuthorizedREQT = Depends(auth_user),
):
    await write_review.for_book(
        user=user,
        review_data=review_data,
    )

    event = UserPersonalRecoEVENT(
        user_id=user.sub,
        type=UserEventENUM.RATING,
        book_id=review_data.book_id,
        metadata=RatingEventMeta(rating=review_data.rating).model_dump(),
    )

    await publish_user_personal_books_reco_rmq_safe(
        routing_key="events.rating",
        event=event,
        correlation_id=str(user.sub),
    )

    return {"detail": "book review created"}