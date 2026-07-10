"""Global answer cache for the agent chat (Redis).

Five users asking «опиши книгу гарри поттер» must not pay for five
LLM turns: the first answer is stored and replayed for everyone.

Only self-contained book-search answers are cached. Never cached:
  - orders / cart / chitchat — personal or context-dependent;
  - messages with anaphora («ещё», «другую», «про это») — their meaning
    depends on the dialog;
  - short contextual words («да», «давай») — answers to the bot's question.
"""

import hashlib
import logging

from app.agents.config.base import (
    AGENT_ANSWER_CACHE_KEY,
    AGENT_ANSWER_CACHE_MIN_CHARS,
    AGENT_ANSWER_CACHE_TTL,
)
from app.agents.smalltalk import _CONTEXTUAL, normalize_message
from app.shared.service.infrastructure.redis.clients import RedisClient

logger = logging.getLogger(__name__)

# tokens that tie a message to the dialog — such messages are not cacheable
_ANAPHORA = {
    "еще", "другое", "другой", "другую", "другие", "дальше", "снова",
    "опять", "продолжи", "продолжай", "повтори", "тоже",
    "это", "эта", "эту", "этот", "этой", "этих", "тот", "ту", "та", "те",
    "их", "его", "ее", "них", "ней", "нем",
    "первый", "первую", "второй", "вторую", "третий", "третью",
    "последний", "последнюю",
    "more", "other", "another", "again", "next", "continue", "repeat",
    "it", "them", "this", "that", "these", "those", "same", "first",
    "second", "last",
}


def is_cacheable(message: str) -> bool:
    normalized = normalize_message(message)

    if len(normalized) < AGENT_ANSWER_CACHE_MIN_CHARS:
        return False

    if normalized in _CONTEXTUAL:
        return False

    return not (set(normalized.split()) & _ANAPHORA)


class AgentAnswerCache:
    def __init__(self, redis: RedisClient):
        self._redis = redis

    @staticmethod
    def _key(message: str) -> str:
        # bag-of-words key: for search queries word order carries no meaning,
        # so «любовные книги» and «книги любовные» share one cache entry
        words = sorted(normalize_message(message).split())
        digest = hashlib.sha256(" ".join(words).encode("utf-8")).hexdigest()
        return AGENT_ANSWER_CACHE_KEY.format(digest=digest)

    async def get(self, message: str) -> str | None:
        if not is_cacheable(message):
            return None

        try:
            return await self._redis.string.get(self._key(message))
        except Exception:
            logger.exception("answer cache get failed")
            return None

    async def set(self, message: str, answer: str) -> None:
        if not is_cacheable(message) or not answer:
            return

        try:
            await self._redis.string.add(
                self._key(message),
                answer,
                ex=AGENT_ANSWER_CACHE_TTL,
            )
        except Exception:
            logger.exception("answer cache set failed")
