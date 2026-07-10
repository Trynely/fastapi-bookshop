import json

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from app.agents.config.base import (
    AGENT_CHAT_HISTORY_KEY,
    AGENT_CHAT_HISTORY_MAX_MESSAGES,
    AGENT_CHAT_HISTORY_TTL,
    AGENT_SHOWN_BOOKS_KEY,
    AGENT_SHOWN_BOOKS_MAX,
)
from app.shared.service.infrastructure.redis.clients import RedisClient


class RedisAgentChatHistory:
    """Sliding-window dialog memory in Redis (per user, with TTL).

    Only user/assistant turns are persisted — tool calls and tool results
    stay inside a single graph run.
    """

    def __init__(self, redis: RedisClient):
        self._redis = redis

    @staticmethod
    def _key(user_id: int) -> str:
        return AGENT_CHAT_HISTORY_KEY.format(user_id=user_id)

    async def load(self, user_id: int) -> list[BaseMessage]:
        raw = await self._redis.string.get(self._key(user_id))

        if not raw:
            return []

        messages: list[BaseMessage] = []

        for item in json.loads(raw):
            if item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
            else:
                messages.append(AIMessage(content=item["content"]))

        return messages

    async def append(
        self,
        user_id: int,
        user_message: str,
        assistant_message: str,
    ) -> None:
        raw = await self._redis.string.get(self._key(user_id))
        history: list[dict] = json.loads(raw) if raw else []

        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_message})

        history = history[-AGENT_CHAT_HISTORY_MAX_MESSAGES:]

        await self._redis.string.add(
            self._key(user_id),
            json.dumps(history, ensure_ascii=False),
            ex=AGENT_CHAT_HISTORY_TTL,
        )


class ShownBooksTracker:
    """Remembers which books were already recommended to a user (with TTL),
    so repeated 'show me more' requests never return the same books.

    Tracks both ids AND title+author keys: the catalog may contain the same
    book under several ids (different editions), so id-only exclusion is
    not enough.

    Needed because tool results (with book ids) live only inside one graph
    run — the dialog history keeps just the text, without ids.
    """

    def __init__(self, redis: RedisClient):
        self._redis = redis

    @staticmethod
    def _key(user_id: int) -> str:
        return AGENT_SHOWN_BOOKS_KEY.format(user_id=user_id)

    @staticmethod
    def book_key(title: str, author: str | None) -> str:
        return f"{title.strip().lower()}|{(author or '').strip().lower()}"

    async def get(self, user_id: int) -> tuple[list[int], set[str]]:
        """Returns (shown ids, shown title+author keys)."""
        raw = await self._redis.string.get(self._key(user_id))

        if not raw:
            return [], set()

        entries = json.loads(raw)

        # tolerate the old format: plain list of ids
        if entries and isinstance(entries[0], int):
            return entries, set()

        return (
            [entry["id"] for entry in entries],
            {entry["key"] for entry in entries},
        )

    async def add(
        self,
        user_id: int,
        books: list[tuple[int, str]],
    ) -> None:
        """books: list of (book_id, title+author key)."""
        shown_ids, _ = await self.get(user_id)
        raw = await self._redis.string.get(self._key(user_id))
        entries = json.loads(raw) if raw else []

        if entries and isinstance(entries[0], int):  # migrate old format
            entries = [{"id": book_id, "key": ""} for book_id in entries]

        known = set(shown_ids)

        for book_id, key in books:
            if book_id not in known:
                entries.append({"id": book_id, "key": key})
                known.add(book_id)

        entries = entries[-AGENT_SHOWN_BOOKS_MAX:]

        await self._redis.string.add(
            self._key(user_id),
            json.dumps(entries, ensure_ascii=False),
            ex=AGENT_CHAT_HISTORY_TTL,
        )
