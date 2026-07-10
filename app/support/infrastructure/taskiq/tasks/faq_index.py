from app.shared.service.infrastructure.taskiq.broker import taskiq_broker
from app.support.db.qdrant.collections.faq import FaqQdrantCollection


@taskiq_broker.task
async def faq_index_task() -> None:
    """Заливка FAQ в Qdrant (идемпотентно: uuid5 -> upsert без дублей)."""
    from app.shared.service.infrastructure.dishka.base import get_container
    container = get_container()

    async with container() as request_container:
        faq_collection = await request_container.get(FaqQdrantCollection)
        await faq_collection.make_index()
