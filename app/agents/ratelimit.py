"""Per-user rate limiting for the agent chat (Redis fixed windows).

Protects the LLM providers from spam and accidental client loops.
Every incoming message is counted — including ones answered from code —
so a runaway client cannot bypass the limits.
"""

import logging

from app.agents.config.base import (
    AGENT_RATE_LIMIT_KEY,
    AGENT_RATE_LIMITS,
    AGENT_TURN_LOCK_KEY,
    AGENT_TURN_LOCK_TTL,
)
from app.shared.service.infrastructure.redis.clients import RedisClient

logger = logging.getLogger(__name__)


class AgentRateLimiter:
    """Fixed windows anchored at the first message: the counter key gets
    a TTL when created, so the window slides naturally as keys expire."""

    def __init__(self, redis: RedisClient):
        self._redis = redis

    async def check(self, user_id: int) -> str | None:
        """Count the message. Returns a refusal text if a limit is hit."""
        try:
            for window, (limit, ttl, message) in AGENT_RATE_LIMITS.items():
                key = AGENT_RATE_LIMIT_KEY.format(user_id=user_id, window=window)

                count = await self._redis.string.incr(key)
                if count == 1:
                    await self._redis.string.expire(key, ttl)

                if count > limit:
                    logger.warning(
                        "agent chat rate limit hit (user_id=%s, window=%s, count=%s)",
                        user_id, window, count,
                    )
                    return message
        except Exception:
            # fail-open: a Redis hiccup must not take the chat down
            logger.exception("rate limiter failed, letting the message through")

        return None

    async def acquire_turn(self, user_id: int) -> bool:
        """One turn at a time: 10 rapid messages must not spawn 10 graph runs.

        The lock has a TTL so a crashed worker cannot deadlock the user.
        """
        key = AGENT_TURN_LOCK_KEY.format(user_id=user_id)

        try:
            acquired = await self._redis.string.add(
                key, "1", ex=AGENT_TURN_LOCK_TTL, nx=True,
            )
            return bool(acquired)
        except Exception:
            logger.exception("turn lock acquire failed, letting the message through")
            return True  # fail-open

    async def release_turn(self, user_id: int) -> None:
        try:
            await self._redis.key.remove(AGENT_TURN_LOCK_KEY.format(user_id=user_id))
        except Exception:
            logger.exception("turn lock release failed (TTL will clean it up)")
