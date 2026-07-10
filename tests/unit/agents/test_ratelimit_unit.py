import pytest

from app.agents.config.base import AGENT_RATE_LIMITS
from app.agents.ratelimit import AgentRateLimiter


class FakeStringClient:
    def __init__(self):
        self.counters: dict[str, int] = {}
        self.ttls: dict[str, int] = {}
        self.locks: dict[str, str] = {}

    async def incr(self, key: str) -> int:
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key: str, seconds: int, nx: bool = False) -> bool:
        self.ttls[key] = seconds
        return True

    async def add(self, key, value, ex=None, nx=False, **kwargs):
        if nx and key in self.locks:
            return None
        self.locks[key] = value
        return True


class FakeKeyClient:
    def __init__(self, store: dict):
        self._store = store

    async def remove(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            removed += self._store.pop(key, None) is not None
        return removed


class FakeRedis:
    def __init__(self):
        self.string = FakeStringClient()
        self.key = FakeKeyClient(self.string.locks)


class BrokenRedis:
    class _Broken:
        async def incr(self, key):
            raise ConnectionError("redis down")

        async def expire(self, key, seconds, nx=False):
            raise ConnectionError("redis down")

    def __init__(self):
        self.string = self._Broken()


MINUTE_LIMIT = AGENT_RATE_LIMITS["minute"][0]


@pytest.mark.asyncio
async def test_allows_up_to_minute_limit():
    limiter = AgentRateLimiter(FakeRedis())

    for _ in range(MINUTE_LIMIT):
        assert await limiter.check(user_id=1) is None


@pytest.mark.asyncio
async def test_blocks_above_minute_limit():
    limiter = AgentRateLimiter(FakeRedis())

    for _ in range(MINUTE_LIMIT):
        await limiter.check(user_id=1)

    refusal = await limiter.check(user_id=1)
    assert refusal == AGENT_RATE_LIMITS["minute"][2]


@pytest.mark.asyncio
async def test_limits_are_per_user():
    limiter = AgentRateLimiter(FakeRedis())

    for _ in range(MINUTE_LIMIT):
        await limiter.check(user_id=1)

    assert await limiter.check(user_id=1) is not None
    assert await limiter.check(user_id=2) is None


@pytest.mark.asyncio
async def test_ttl_set_once_per_window():
    redis = FakeRedis()
    limiter = AgentRateLimiter(redis)

    await limiter.check(user_id=1)
    await limiter.check(user_id=1)

    for window, (_, ttl, _) in AGENT_RATE_LIMITS.items():
        key = f"agent:chat:rl:1:{window}"
        assert redis.string.ttls[key] == ttl


@pytest.mark.asyncio
async def test_fail_open_when_redis_is_down():
    limiter = AgentRateLimiter(BrokenRedis())

    assert await limiter.check(user_id=1) is None


@pytest.mark.asyncio
async def test_turn_lock_blocks_parallel_turns():
    limiter = AgentRateLimiter(FakeRedis())

    assert await limiter.acquire_turn(user_id=1) is True
    assert await limiter.acquire_turn(user_id=1) is False  # busy
    assert await limiter.acquire_turn(user_id=2) is True   # other user is free

    await limiter.release_turn(user_id=1)
    assert await limiter.acquire_turn(user_id=1) is True
