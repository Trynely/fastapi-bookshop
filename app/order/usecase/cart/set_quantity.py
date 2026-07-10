from app.order.db.sqlalchemy.repositories.cart import (
    CartItemSQLAlchemyRepository,
    CartSQLAlchemyRepository,
)
from app.order.exceptions.cart import (
    BookStockExceededERR,
    CartItemNotFoundERR,
)
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.exceptions import BookNotFoundERR, BookUnavailableERR
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.base import is_exists

class SetCartItemQuantity:
    """
    Устанавливает количество позиции в корзине.
    quantity == 0 — позиция удаляется из корзины.
    Количество проверяется по актуальному остатку книги (book.quantity).
    """

    def __init__(
        self,
        transaction: SQLAlchemyTransaction,
        book_repository: BookSQLAlchemyREPO,
        cart_repository: CartSQLAlchemyRepository,
        cart_item_repository: CartItemSQLAlchemyRepository,
    ):
        self._transaction = transaction
        self.book_repository = book_repository
        self.cart_repository = cart_repository
        self.cart_item_repository = cart_item_repository

    async def set(self, user_id: int, book_id: int, quantity: int) -> int:
        async with self._transaction:
            cart = await is_exists(
                self.cart_repository.get_by_user_id(user_id=user_id),
                CartItemNotFoundERR(),
            )

            item = await is_exists(
                self.cart_item_repository.get_by_cart_and_book_id(
                    cart_id=cart.id,
                    book_id=book_id,
                ),
                CartItemNotFoundERR(),
            )

            if quantity == 0:
                await self.cart_item_repository.remove(item)
                return 0

            book = await is_exists(
                self.book_repository.get_by_id(id=book_id),
                BookNotFoundERR(),
            )

            if not book.is_available:
                raise BookUnavailableERR()

            # проверка по актуальному остатку на складе
            if quantity > book.quantity:
                raise BookStockExceededERR(available=book.quantity)

            item.quantity = quantity
            return quantity
