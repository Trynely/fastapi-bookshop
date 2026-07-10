import asyncio
from aio_pika import (
    Exchange,
    ExchangeType,
    RobustConnection,
    RobustChannel,
    connect_robust,
)
from app.core.config.base import get_settings

settings = get_settings()

_connection: RobustConnection | None = None
_channel: RobustChannel | None = None
_lock = asyncio.Lock()

async def get_rabbitmq_channel() -> RobustChannel:
    global _connection, _channel

    if _channel is None or _channel.is_closed:
        async with _lock:
            if _connection is None or _connection.is_closed:
                _connection = await connect_robust(settings.rabbitmq.url)

            if _channel is None or _channel.is_closed:
                _channel = await _connection.channel()

    return _channel


_exchanges_cache: dict[str, Exchange] = {}

async def get_exchange(
    *,
    exchange_name: str,
    exchange_type: ExchangeType,
    durable: bool = True,
) -> Exchange:
    """
    Кэширует exchanges, чтобы не делать
    declare_exchange() на каждый publish.
    """

    cached = _exchanges_cache.get(exchange_name)

    if cached is not None:
        return cached

    channel = await get_rabbitmq_channel()

    exchange = await channel.declare_exchange(
        exchange_name,
        exchange_type,
        durable=durable,
    )

    _exchanges_cache[exchange_name] = exchange

    return exchange


async def close_rabbitmq():
    global _connection, _channel

    async with _lock:
        if _channel and not _channel.is_closed:
            await _channel.close()

        if _connection and not _connection.is_closed:
            await _connection.close()

        _channel = None
        _connection = None