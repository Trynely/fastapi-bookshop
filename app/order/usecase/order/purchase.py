import asyncio
import time
from decimal import Decimal, ROUND_HALF_UP

import stripe
from sqlalchemy.exc import DBAPIError

from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO
from app.client.exception.user.exists import UserNotFoundERR
from app.core.config.base import get_settings
from app.order.api.requests.order.create import CreateOrderREQT
from app.order.db.models.order import (
    OrderItemModel,
    OrderModel,
    OrderStatusENUM,
    PaymentMethodENUM,
    PaymentModel,
    PaymentStatusENUM,
)
from app.order.db.sqlalchemy.repositories.order import (
    OrderSQLAlchemyRepository,
    PaymentSQLAlchemyRepository,
)
from app.order.dto.order.checkout import CheckoutResultDTO
from app.order.usecase.order.cancel import CancelOrder
from app.order.exceptions.order import (
    BooksBusyERR,
    OrderBookNotAvailableERR,
    OrderItemsLimitExceededERR,
    OrderQuantityInvalidERR,
    StripeCheckoutERR,
)
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.base import is_exists

settings = get_settings()
stripe.api_key = settings.stripe.secret_key

# SQLSTATE 55P03 — lock_not_available:
# строки уже заблокированы другой транзакцией (FOR UPDATE NOWAIT)
_LOCK_NOT_AVAILABLE = "55P03"


def _is_lock_not_available(exc: DBAPIError) -> bool:
    orig = exc.orig
    code = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
    return code == _LOCK_NOT_AVAILABLE or _LOCK_NOT_AVAILABLE in str(orig)


class BuyBooks:
    def __init__(
        self,
        transaction: SQLAlchemyTransaction,
        book_repository: BookSQLAlchemyREPO,
        user_repository: UserSQLAlchemyREPO,
        order_repository: OrderSQLAlchemyRepository,
        payment_repository: PaymentSQLAlchemyRepository,
    ):
        self._transaction = transaction
        self.book_repository = book_repository
        self.user_repository = user_repository
        self.order_repository = order_repository
        self.payment_repository = payment_repository
        self._cancel_order = CancelOrder(
            transaction=transaction,
            order_repository=order_repository,
            payment_repository=payment_repository,
            book_repository=book_repository,
        )

    async def buy(
        self,
        user_id: int,
        order_data: CreateOrderREQT,
        payment_method: PaymentMethodENUM = PaymentMethodENUM.CARD,
    ) -> CheckoutResultDTO:
        items = order_data.items

        if not 1 <= len(items) <= 10:
            raise OrderItemsLimitExceededERR()

        book_ids = [item.book_id for item in items]

        # --- транзакция 1: резервируем книги, создаём заказ и платёж ---
        async with self._transaction:
            session = self.order_repository.session

            user = await is_exists(
                self.user_repository.get_by_id(id=user_id),
                UserNotFoundERR(),
            )

            try:
                books = await self.book_repository.get_list_by_ids_for_update(book_ids)
            except DBAPIError as e:
                if _is_lock_not_available(e):
                    # книги прямо сейчас покупает кто-то другой -> 409
                    raise BooksBusyERR() from e
                raise

            books_map = {book.id: book for book in books}

            total_amount = Decimal("0")
            order_items: list[OrderItemModel] = []

            for item in items:
                if item.quantity <= 0:
                    raise OrderQuantityInvalidERR()

                book = books_map.get(item.book_id)

                if book is None or not book.is_available:
                    raise OrderBookNotAvailableERR(item.book_id)

                if book.quantity < item.quantity:
                    raise OrderBookNotAvailableERR(book.id)

                # резервируем книги
                book.quantity -= item.quantity

                total_amount += book.price * Decimal(item.quantity)

                order_items.append(
                    OrderItemModel(
                        book_id=book.id,
                        quantity=item.quantity,
                        price=book.price,
                    )
                )

            order = OrderModel(
                user_id=user.id,
                total_amount=total_amount,
                status=OrderStatusENUM.PENDING,
                items=order_items,
            )
            session.add(order)

            payment = PaymentModel(
                amount=total_amount,
                method=payment_method,
                status=PaymentStatusENUM.PENDING,
                order=order,
            )
            session.add(payment)

            await session.flush()

            order_id = order.id
            payment_id = payment.id
            user_username = user.username
            user_email = user.email

        # --- Stripe (вне транзакции) ---

        def create_checkout() -> stripe.checkout.Session:
            customer = stripe.Customer.create(
                name=user_username,
                email=user_email,
            )

            line_items = []

            for item in items:
                book = books_map[item.book_id]

                unit_amount = int(
                    (book.price * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
                )

                line_items.append(
                    {
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": unit_amount,
                            "product_data": {"name": book.title},
                        },
                        "quantity": item.quantity,
                    }
                )

            return stripe.checkout.Session.create(
                mode="payment",
                payment_method_types=["card"],
                customer=customer.id,
                expires_at=int(time.time()) + settings.stripe.checkout_ttl_minutes * 60,
                line_items=line_items,
                idempotency_key=f"payment_{payment_id}",
                success_url=settings.stripe.success_url.format(order_id=order_id),
                cancel_url=settings.stripe.cancel_url.format(order_id=order_id),
                metadata={
                    "order_id": str(order_id),
                    "payment_id": str(payment_id),
                },
            )

        try:
            checkout_session = await asyncio.to_thread(create_checkout)
        except Exception as e:
            # снимаем резерв книг и помечаем платёж/заказ проваленными
            await self._cancel_order.cancel(order_id)
            raise StripeCheckoutERR() from e

        # --- транзакция 2: сохраняем id checkout-сессии ---
        async with self._transaction:
            payment = await self.payment_repository.get_by_id(id=payment_id)
            payment.transaction_id = checkout_session.id

        return CheckoutResultDTO(
            order_id=order_id,
            payment_id=payment_id,
            stripe_checkout_url=checkout_session.url,
        )
