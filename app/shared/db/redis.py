import json
import functools
from typing import (
    Awaitable,
    Callable,
    Optional,
    Type,
    TypeVar,
)

from pydantic import TypeAdapter
from app.core.db.redis import get_redis
from pydantic.json import pydantic_encoder
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")

def redis_cache(
    key_builder: Callable[..., str],
    ttl: int = 60,
    response_model: Optional[Type[T]] = None,
):
    def decorator(func: Callable[..., Awaitable[T]]):
        adapter = TypeAdapter(response_model) if response_model else None

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            redis = get_redis()
            cache_key = f"{key_builder(*args, **kwargs)}"

            try:
                cached = await redis.get(cache_key)
                if cached is not None:
                    if adapter:
                        return adapter.validate_json(cached)
                    return json.loads(cached)
            except Exception as e:
                logger.exception("Cache read error", exc_info=e)

            result = await func(*args, **kwargs)

            try:
                if adapter:
                    serialized = adapter.dump_json(result)
                else:
                    serialized = json.dumps(result, default=pydantic_encoder)

                await redis.set(
                    cache_key,
                    serialized,
                    ex=max(1, ttl),
                )
            except Exception as e:
                logger.exception("Cache write error", exc_info=e)

            return result

        return wrapper
    return decorator