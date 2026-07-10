import pytest

from app.agents.cache import AgentAnswerCache, is_cacheable


class FakeStringClient:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key):
        return self.store.get(key)

    async def add(self, key, value, ex=None, nx=False, **kwargs):
        self.store[key] = value
        if ex:
            self.ttls[key] = ex
        return True


class FakeRedis:
    def __init__(self):
        self.string = FakeStringClient()


@pytest.mark.parametrize(
    "message",
    [
        "опиши книгу гарри поттер",
        "какие книги есть по Python?",
        "посоветуй фантастику на вечер",
        "книги Достоевского дешевле 20 евро",
    ],
)
def test_selfcontained_queries_are_cacheable(message: str):
    assert is_cacheable(message) is True


@pytest.mark.parametrize(
    "message",
    [
        "да",                      # contextual
        "давай",                   # contextual
        "ещё",                     # anaphora + too short
        "покажи другую",           # anaphora
        "расскажи про это",        # anaphora
        "добавь первую в корзину", # anaphora
        "а что про них думаешь",   # anaphora
        "show me more",            # anaphora (en)
        "хм",                      # too short
    ],
)
def test_context_dependent_queries_are_not_cacheable(message: str):
    assert is_cacheable(message) is False


@pytest.mark.asyncio
async def test_roundtrip_and_normalization():
    cache = AgentAnswerCache(FakeRedis())

    await cache.set("Опиши книгу Гарри Поттер", "Вот описание...")

    # different spelling/punctuation of the same question hits the cache
    assert await cache.get("опиши книгу гарри поттер!") == "Вот описание..."
    assert await cache.get("ОПИШИ  КНИГУ  ГАРРИ  ПОТТЕР") == "Вот описание..."
    assert await cache.get("опиши книгу властелин колец") is None


@pytest.mark.asyncio
async def test_word_order_does_not_matter():
    cache = AgentAnswerCache(FakeRedis())

    await cache.set("любовные книги", "Вот книги о любви...")

    assert await cache.get("книги любовные") == "Вот книги о любви..."
    assert await cache.get("Книги — любовные!") == "Вот книги о любви..."
    assert await cache.get("любовные романы") is None


@pytest.mark.asyncio
async def test_uncacheable_message_is_never_stored():
    redis = FakeRedis()
    cache = AgentAnswerCache(redis)

    await cache.set("давай", "ответ")
    await cache.set("покажи другую", "ответ")

    assert redis.string.store == {}


@pytest.mark.asyncio
async def test_empty_answer_is_not_stored():
    redis = FakeRedis()
    cache = AgentAnswerCache(redis)

    await cache.set("опиши книгу гарри поттер", "")

    assert redis.string.store == {}
