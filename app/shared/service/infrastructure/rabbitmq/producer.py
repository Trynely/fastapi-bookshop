from datetime import UTC, datetime
from uuid import uuid4
import aio_pika
from typing import Protocol, runtime_checkable

from pydantic import BaseModel
from app.shared.service.infrastructure.rabbitmq.connection import (
    get_exchange,
    get_rabbitmq_channel,
)

@runtime_checkable
class DataclassInstance(Protocol):
    __dataclass_fields__: dict


async def publish_rmq(
    *,
    routing_key: str,
    event: BaseModel,

    exchange_name: str | None = None,
    exchange_type: aio_pika.ExchangeType = aio_pika.ExchangeType.DIRECT,

    correlation_id: str | None = None,
    headers: dict | None = None,
) -> None:
    channel = await get_rabbitmq_channel()

    body = event.model_dump_json().encode("utf-8")

    message = aio_pika.Message(
        body=body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,

        message_id=str(uuid4()),
        correlation_id=correlation_id,
        timestamp=datetime.now(UTC),

        headers=headers or {},
    )

    if exchange_name is None:
        exchange = channel.default_exchange
    else:
        exchange = await get_exchange(
            exchange_name=exchange_name,
            exchange_type=exchange_type,
        )

    await exchange.publish(
        message,
        routing_key=routing_key,
    )