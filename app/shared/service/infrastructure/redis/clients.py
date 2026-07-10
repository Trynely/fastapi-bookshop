import redis.asyncio as redis
from typing import Any, Dict, List, Optional
from app.shared.service.infrastructure.base import to_json
from app.shared.service.infrastructure.redis.base import BaseRedisClient

class RedisStringClient(BaseRedisClient):
    async def add(
        self,
        key: str,
        value: Any,
        ex: int | None = None,
        nx: bool = False,
        xx: bool = False,
        **kwargs,
    ):
        if isinstance(value, (dict, list)):
            value = to_json(value)

        return await self.redis.set(
            key,
            value,
            ex=ex,
            nx=nx,
            xx=xx,
            **kwargs,
        )

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def incr(self, key: str) -> int:
        return await self.redis.incr(key)

    async def expire(self, key: str, seconds: int, nx: bool = False) -> bool:
        return await self.redis.expire(key, seconds, nx=nx)


class RedisSetClient(BaseRedisClient):
    async def add(self, key: str, *values: str) -> int:
        return await self.redis.sadd(key, *values)

    async def remove(self, key: str, *values: str) -> int:
        return await self.redis.srem(key, *values)

    async def get(self, key: str) -> List[str]:
        return await self.redis.smembers(key)

    async def exists(self, key: str, value: str) -> bool:
        return await self.redis.sismember(key, value)


class RedisSortedSetClient(BaseRedisClient):
    async def add(self, key: str, mapping: dict[str, float]):
        return await self.redis.zadd(key, mapping)

    async def remove(self, key: str, *values: str):
        return await self.redis.zrem(key, *values)

    async def range(self, key: str, start: int, stop: int):
        return await self.redis.zrange(key, start, stop)

    async def count(self, key: str):
        return await self.redis.zcard(key)
    

class RedisHashClient(BaseRedisClient):
    async def hset(self, key: str, mapping: Dict[str, Any]) -> int:
        return await self.redis.hset(key, mapping=mapping)

    async def hget(self, key: str, field: str):
        return await self.redis.hget(key, field)

    async def hgetall(self, key: str):
        return await self.redis.hgetall(key)

    async def hdel(self, key: str, *fields: str) -> int:
        return await self.redis.hdel(key, *fields)


class RedisListClient(BaseRedisClient):
    async def lpush(self, key: str, *values: str) -> int:
        return await self.redis.lpush(key, *values)

    async def rpush(self, key: str, *values: str) -> int:
        return await self.redis.rpush(key, *values)

    async def lpop(self, key: str) -> Optional[str]:
        return await self.redis.lpop(key)

    async def rpop(self, key: str) -> Optional[str]:
        return await self.redis.rpop(key)

    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        return await self.redis.lrange(key, start, stop)

    async def ltrim(self, key: str, start: int, stop: int) -> bool:
        return await self.redis.ltrim(key, start, stop)


class RedisKeyClient(BaseRedisClient):
    async def remove(self, *keys: str) -> int:
        return await self.redis.delete(*keys)

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key) > 0

    async def keys(self, pattern: str = "*") -> List[str]:
        return await self.redis.keys(pattern)

    async def expire(self, key: str, ttl: int) -> bool:
        return await self.redis.expire(key, ttl)

    async def ttl(self, key: str) -> int:
        return await self.redis.ttl(key)

    async def flush_all(self):
        await self.redis.flushdb()


class RedisClient:
    def __init__(self, redis: redis.Redis):
        self.string = RedisStringClient(redis)
        self.set = RedisSetClient(redis)
        self.sorted_set = RedisSortedSetClient(redis)
        self.hash = RedisHashClient(redis)
        self.list = RedisListClient(redis)
        self.key = RedisKeyClient(redis)