import redis.asyncio as redis
from typing import Optional
from app.core.config.base import get_settings

settings = get_settings()

_redis: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _redis

    if _redis is None:
        _redis = redis.from_url(
            settings.redis.url,
            encoding="utf-8",
            decode_responses=True,
        )

    return _redis


async def close_redis() -> None:
    global _redis

    if _redis is not None:
        await _redis.aclose()
        _redis = None