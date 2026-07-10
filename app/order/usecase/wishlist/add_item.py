from app.client.exception.user.exists import UserNotFoundERR
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.exceptions import BookNotFoundERR
from app.shared.service.infrastructure.base import is_exists
from app.order.exceptions.wishlist import WishlistItemAlreadyExists
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO

class AddBookToWishlist:
    def __init__(
        self,
        transaction: SQLAlchemyTransaction,
        book_repository: BookSQLAlchemyREPO,
        user_repository: UserSQLAlchemyREPO,
    ):
        self._transaction = transaction
        self.book_repository = book_repository
        self.user_repository = user_repository

    async def add(self, user_id: int, book_id: int) -> None:
        book = await is_exists(
            self.book_repository.get_by_id(id=book_id),
            BookNotFoundERR(),
        )

        user = await is_exists(
            self.user_repository.get_by_id(id=user_id),
            UserNotFoundERR(),
        )

        already_exists = await self.book_repository.is_in_wishlist(
            user_id=user_id,
            book_id=book_id,
        )
        if already_exists:
            raise WishlistItemAlreadyExists()

        user.wishlist.append(book)
        await self._transaction.commit()