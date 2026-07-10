from sqlalchemy import select
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.order.api.responses.wishlist.base import WishlistItemsResponse

class WishlistFilterQH:
    def __init__(self, book_repository: BookSQLAlchemyREPO):
        self.book_repository = book_repository

    async def get_wishlist_items_by_user(self, user_id: int) -> WishlistItemsResponse:
        books = await self.book_repository.get_list_by_wishlist_user_id(user_id=user_id)

        return [
            WishlistItemsResponse.model_validate(book)
            for book in books
        ]
        