from app.order.db.models.order import (
    OrderStatusENUM,
    PaymentStatusENUM,
)
from app.order.db.sqlalchemy.repositories.cart import CartSQLAlchemyRepository
from app.order.db.sqlalchemy.repositories.order import (
    OrderSQLAlchemyRepository,
    PaymentSQLAlchemyRepository,
)
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction

class ConfirmOrderPayment:
    """
    Обработка события `checkout.session.completed` от Stripe:
    платёж -> SUCCESS, заказ -> PAID, корзина покупателя очищается.
    """

    def __init__(
        self,
        transaction: SQLAlchemyTransaction,
        order_repository: OrderSQLAlchemyRepository,
        payment_repository: PaymentSQLAlchemyRepository,
        cart_repository: CartSQLAlchemyRepository,
    ):
        self._transaction = transaction
        self.order_repository = order_repository
        self.payment_repository = payment_repository
        self.cart_repository = cart_repository

    async def confirm(
        self,
        order_id: int,
        payment_id: int,
        payment_intent_id: str | None = None,
    ) -> None:
        async with self._transaction:
            payment = await self.payment_repository.get_by_id(id=payment_id)

            if payment:
                # idempotency: Stripe может слать webhook повторно
                if payment.status == PaymentStatusENUM.SUCCESS:
                    return

                payment.status = PaymentStatusENUM.SUCCESS
                payment.payment_intent_id = payment_intent_id

            order = await self.order_repository.get_by_id_with_items(order_id)

            if order:
                order.status = OrderStatusENUM.PAID
                # заказ оплачен — убираем из корзины только купленные книги,
                # невыбранные позиции остаются
                await self.cart_repository.remove_items_by_user_and_books(
                    user_id=order.user_id,
                    book_ids=[item.book_id for item in order.items],
                )
