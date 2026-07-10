import asyncio
import logging
import aio_pika
from aio_pika.abc import (
    AbstractIncomingMessage,
    AbstractQueue,
)
from app.client.api.events.user.personal_reco import (
    UserPersonalRecoEVENT,
)
from app.client.service.infrastructure.rabbitmq.producer.reco_events import USER_EVENTS_EXCHANGE_NAME
from app.product.service.usecase.book.personal_reco import BookPersonalRecoForUserUC
from app.shared.service.infrastructure.dishka.base import get_container
from app.shared.service.infrastructure.rabbitmq.connection import (
    get_rabbitmq_channel,
)

logger = logging.getLogger(__name__)

PERSONAL_RECO_QUEUE_NAME = "personal_book_reco"
USER_EVENTS_DLX_NAME = "user_events_dlx"
PERSONAL_RECO_EVENTS_DLQ_NAME = "personal_book_reco_dlq"

async def _declare_topology() -> AbstractQueue:
    channel = await get_rabbitmq_channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        USER_EVENTS_EXCHANGE_NAME,
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    dlx = await channel.declare_exchange(
        USER_EVENTS_DLX_NAME,
        aio_pika.ExchangeType.FANOUT,
        durable=True,
    )

    queue = await channel.declare_queue(
        PERSONAL_RECO_QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": USER_EVENTS_DLX_NAME,
        },
    )

    dlq = await channel.declare_queue(
        PERSONAL_RECO_EVENTS_DLQ_NAME,
        durable=True,
    )

    await queue.bind(
        exchange,
        routing_key="events.#",
    )

    await dlq.bind(dlx)
    return queue


async def _process_message(
    message: AbstractIncomingMessage,
) -> None:
    try:
        async with message.process(requeue=False):
            event = (
                UserPersonalRecoEVENT
                .model_validate_json(message.body)
            )

            container = get_container()

            async with container() as request_container:
                book_personal_reco_uc = await request_container.get(BookPersonalRecoForUserUC)
                await book_personal_reco_uc.generate(event)
    except Exception:
        logger.exception(
            "Failed to process recommendation event"
        )
        raise


async def start_consumer(queue: AbstractQueue) -> None:
    consumer_tag = await queue.consume(
        _process_message
    )

    logger.info(
        "Recommendation consumer started"
    )

    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        logger.info(
            "Stopping recommendation consumer..."
        )

        await queue.cancel(consumer_tag)
        raise