import logging

import aio_pika
from pydantic import BaseModel
from app.shared.service.infrastructure.rabbitmq.producer import publish_rmq

logger = logging.getLogger(__name__)

USER_EVENTS_EXCHANGE_NAME = "user_events"

async def publish_user_personal_books_reco_rmq(
    *,
    routing_key: str,
    event: BaseModel,
    correlation_id: str | None = None,
) -> None:
    await publish_rmq(
        exchange_name=USER_EVENTS_EXCHANGE_NAME,
        exchange_type=aio_pika.ExchangeType.TOPIC,

        routing_key=routing_key,
        event=event,

        correlation_id=correlation_id,

        headers={
            "event_type": event.__class__.__name__,
        },
    )


async def publish_user_personal_books_reco_rmq_safe(
    *,
    routing_key: str,
    event: BaseModel,
    correlation_id: str | None = None,
) -> None:
    """
        Fire-and-forget вариант для роутеров: reco-событие — побочный
        сигнал, деградация RabbitMQ не должна ронять основной запрос
        (добавление в корзину/избранное и т.п.) пятисоткой.
    """

    try:
        await publish_user_personal_books_reco_rmq(
            routing_key=routing_key,
            event=event,
            correlation_id=correlation_id,
        )
    except Exception:
        logger.exception(
            "Failed to publish user reco event",
            extra={
                "routing_key": routing_key,
                "correlation_id": correlation_id,
            },
        )