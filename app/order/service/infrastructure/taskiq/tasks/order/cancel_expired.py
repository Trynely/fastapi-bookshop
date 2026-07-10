import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import DBAPIError

from app.core.config.base import get_settings
from app.core.db.postgres import db_helper
from app.order.db.sqlalchemy.repositories.order import (
    OrderSQLAlchemyRepository,
    PaymentSQLAlchemyRepository,
)
from app.order.usecase.order.cancel import CancelOrder
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker

logger = logging.getLogger(__name__)

# буфер сверх TTL checkout-сессии: обычно протухший заказ отменяет
# webhook `checkout.session.expired`, задача — страховка на случай,
# если webhook потерялся или процесс упал между транзакциями BuyBooks
EXPIRE_BUFFER_MINUTES = 10


@taskiq_broker.task(
    task_name="cancel_expired_pending_orders",
    schedule=[{"cron": "*/10 * * * *"}],  # каждые 10 минут
)
async def cancel_expired_pending_orders() -> None:
    settings = get_settings()
    ttl_minutes = settings.stripe.checkout_ttl_minutes + EXPIRE_BUFFER_MINUTES
    cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=ttl_minutes)

    async with db_helper.session_factory() as session:
        order_repository = OrderSQLAlchemyRepository(session)

        expired_ids = await order_repository.get_expired_pending_ids(cutoff)

        if not expired_ids:
            return

        cancel = CancelOrder(
            transaction=SQLAlchemyTransaction(session),
            order_repository=order_repository,
            payment_repository=PaymentSQLAlchemyRepository(session),
            book_repository=BookSQLAlchemyREPO(session),
        )

        canceled = 0
        # каждый заказ — в своей транзакции: сбой одного не мешает остальным
        for order_id in expired_ids:
            try:
                if await cancel.cancel(order_id):
                    canceled += 1
            except DBAPIError:
                # книги заказа заблокированы (NOWAIT) — пропускаем,
                # подберём на следующем запуске
                await session.rollback()
                logger.warning(
                    "cancel_expired_pending_orders: order %d skipped (rows locked)",
                    order_id,
                )
            except Exception:
                await session.rollback()
                logger.exception(
                    "cancel_expired_pending_orders: order %d failed",
                    order_id,
                )

        logger.info(
            "cancel_expired_pending_orders: canceled %d of %d expired orders",
            canceled,
            len(expired_ids),
        )
