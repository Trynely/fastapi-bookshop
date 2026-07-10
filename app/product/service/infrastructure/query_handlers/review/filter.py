from app.product.api.responses.review.preview import ReviewPreviewRESP, ReviewsPreviewPaginationRESP
from app.product.db.postgres.repositories.sqlalchemy.review import BookReviewSQLAlchemyREPO
from app.shared.api.requests.offset_pagination import OffsetPagination

class BookReviewFilterQH:
    def __init__(self, review_repository: BookReviewSQLAlchemyREPO):
        self.review_repository = review_repository

    async def get_reviews_by_book(
        self,
        book_slug: str,
        pagination: OffsetPagination,
    ) -> ReviewsPreviewPaginationRESP:
        result = await self.review_repository.get_list_by_book_slug(
            book_slug=book_slug,
            pagination=pagination,
        )

        return ReviewsPreviewPaginationRESP(
            reviews=[
                ReviewPreviewRESP.model_validate(review)
                for review in result.items
            ],
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            pages=result.pages,
        )