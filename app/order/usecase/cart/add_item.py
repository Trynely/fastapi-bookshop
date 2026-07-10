from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.exceptions import BookNotFoundERR, BookUnavailableERR
from app.shared.service.infrastructure.base import is_exists
from app.order.db.models.cart import CartItemModel, CartModel
from app.order.db.sqlalchemy.repositories.cart import CartItemSQLAlchemyRepository, CartSQLAlchemyRepository
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction

class AddBookToCart:
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

    async def add(self, user_id: int, book_id: int) -> None:
        async with self._transaction:
            book = await is_exists(
                self.book_repository.get_by_id(id=book_id),
                BookNotFoundERR(),
            )

            if not book.is_available:
                raise BookUnavailableERR()

            cart = await self.cart_repository.get_by_user_id(user_id=user_id)

            if not cart:
                cart = CartModel(user_id=user_id)
                cart = await self.cart_repository.save(cart)

            item = await self.cart_item_repository.get_by_cart_and_book_id(
                cart_id=cart.id,
                book_id=book_id,
            )

            if item:
                item.quantity += 1
            else:
                item = CartItemModel(
                    cart_id=cart.id,
                    book_id=book_id,
                    quantity=1,
                )
                await self.cart_item_repository.save(item)
