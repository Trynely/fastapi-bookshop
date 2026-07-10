from app.client.exception.user.exists import UserNotFoundERR
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.exceptions import BookNotFoundERR
from app.shared.service.infrastructure.base import is_exists
from app.order.exceptions.wishlist import WishlistItemNotFound
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO

class RemoveBookFromWishlist:
    def __init__(
        self,
        transaction: SQLAlchemyTransaction,
        book_repository: BookSQLAlchemyREPO,
        user_repository: UserSQLAlchemyREPO,
    ):
        self._transaction = transaction
        self.book_repository = book_repository
        self.user_repository = user_repository

    async def remove(self, user_id: int, book_id: int) -> None:
        book = await is_exists(
            self.book_repository.get_by_id(id=book_id),
            BookNotFoundERR(),
        )

        user = await is_exists(
            self.user_repository.get_by_id(id=user_id),
            UserNotFoundERR(),
        )

        exists = await self.book_repository.is_in_wishlist(
            user_id=user_id,
            book_id=book_id,
        )
        if not exists:
            raise WishlistItemNotFound()

        await self.book_repository.remove_from_wishlist(
            user_id=user_id,
            book_id=book_id,
        )
        await self._transaction.commit()