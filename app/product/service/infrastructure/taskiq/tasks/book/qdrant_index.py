import logging

import redis.asyncio as redis

from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.db.qdrant.collections.books import BooksQdrantCollection
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker

logger = logging.getLogger(__name__)

REINDEX_LOCK_KEY = "locks:qdrant_books_reindex"
REINDEX_LOCK_TTL = 900  # сек; страховка, если воркер умер не сняв лок


@taskiq_broker.task(schedule=[{"cron": "*/15 * * * *"}])
async def qdrant_index_books_task():
    """
    Реконсиляция books-коллекции с Postgres.
    Дёшево (хэши), поэтому крутится по cron + при старте приложения.
    """
    from app.shared.service.infrastructure.dishka.base import get_container
    container = get_container()

    async with container() as request_container:
        redis_client = await request_container.get(redis.Redis)

        # лок: рестарт нескольких реплик / cron не должны реиндексировать параллельно
        acquired = await redis_client.set(
            REINDEX_LOCK_KEY, "1",
            nx=True,
            ex=REINDEX_LOCK_TTL,
        )

        if not acquired:
            logger.info("qdrant books reindex already running, skipping")
            return

        try:
            book_repository = await request_container.get(BookSQLAlchemyREPO)
            books_qdrant_collection = await request_container.get(
                BooksQdrantCollection,
            )

            books = await book_repository.get_books_for_indexing()
            stats = await books_qdrant_collection.reconcile(books)

            logger.info("qdrant books reconcile: %s", stats)
        finally:
            await redis_client.delete(REINDEX_LOCK_KEY)
