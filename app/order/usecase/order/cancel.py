from app.order.db.models.order import (
    OrderStatusENUM,
    PaymentStatusENUM,
)
from app.order.db.sqlalchemy.repositories.order import (
    OrderSQLAlchemyRepository,
    PaymentSQLAlchemyRepository,
)
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction

class CancelOrder:
    """
    Идемпотентная отмена заказа: заказ -> CANCELED, платёж -> FAILED,
    зарезервированные книги возвращаются на склад.

    Отменяет только PENDING-заказы: оплаченный (PAID) или уже отменённый
    заказ не трогается — безопасно вызывать повторно (webhook-и Stripe
    могут дублироваться, фоновая задача может пересечься с webhook).
    """

    def __init__(
        self,
        transaction: SQLAlchemyTransaction,
        order_repository: OrderSQLAlchemyRepository,
        payment_repository: PaymentSQLAlchemyRepository,
        book_repository: BookSQLAlchemyREPO,
    ):
        self._transaction = transaction
        self.order_repository = order_repository
        self.payment_repository = payment_repository
        self.book_repository = book_repository

    async def cancel(self, order_id: int) -> bool:
        """Возвращает True, если заказ был отменён этим вызовом."""
        async with self._transaction:
            order = await self.order_repository.get_by_id_with_items(order_id)

            if order is None or order.status != OrderStatusENUM.PENDING:
                return False

            order.status = OrderStatusENUM.CANCELED

            payment = order.payment
            if payment and payment.status != PaymentStatusENUM.SUCCESS:
                payment.status = PaymentStatusENUM.FAILED

            # возвращаем книги на склад (блокировка в порядке id — без deadlock)
            book_ids = sorted({item.book_id for item in order.items})
            books = await self.book_repository.get_list_by_ids_for_update(book_ids)
            books_map = {book.id: book for book in books}

            for item in order.items:
                book = books_map.get(item.book_id)
                if book:
                    book.quantity += item.quantity

            return True
