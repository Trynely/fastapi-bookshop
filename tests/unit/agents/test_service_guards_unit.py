import pytest

from app.agents.config.base import AGENT_MESSAGE_MAX_CHARS
from app.agents.service import AgentChatService


def make_service(**kwargs) -> AgentChatService:
    """Service with stubbed-out deps: guard paths must not touch them."""
    return AgentChatService(
        llm_factory=None,
        embedder=None,
        books_qdrant_repo=None,
        agent_books_repo=None,
        order_repo=None,
        add_to_cart_uc=None,
        history=None,
        **kwargs,
    )


async def collect(stream):
    return [event async for event in stream]


@pytest.mark.asyncio
async def test_oversized_message_is_refused_without_any_calls():
    service = make_service()
    message = "а" * (AGENT_MESSAGE_MAX_CHARS + 1)

    events = await collect(service.stream_chat(user_id=1, message=message))

    assert [e["event"] for e in events] == ["token", "done"]
    assert "длинн" in events[0]["data"]


@pytest.mark.asyncio
async def test_message_at_limit_passes_the_length_guard():
    service = make_service()
    message = "а" * AGENT_MESSAGE_MAX_CHARS

    # length guard passed -> the turn reaches history.load(None) and dies there;
    # stream_chat must not have yielded the "too long" refusal
    with pytest.raises(AttributeError):
        await collect(service.stream_chat(user_id=1, message=message))


class LimitedRateLimiter:
    async def check(self, user_id):
        return "Вы отправляете сообщения слишком часто. Попробуйте через минуту."


@pytest.mark.asyncio
async def test_rate_limit_fires_before_length_guard():
    service = make_service(rate_limiter=LimitedRateLimiter())
    message = "а" * (AGENT_MESSAGE_MAX_CHARS + 1)

    events = await collect(service.stream_chat(user_id=1, message=message))

    assert "слишком часто" in events[0]["data"]
