"""
Событийная синхронизация одной книги: Postgres -> Qdrant + Elasticsearch.

Запускается из хуков в местах изменения книги (админка).
Полная переиндексация (cron / ручной эндпоинт) остаётся страховкой
на случай потерянных событий.
"""

import logging

from app.product.db.elasticsearch.repositories.books import BooksElasticREPO
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.db.qdrant.collections.books import BooksQdrantCollection
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker

logger = logging.getLogger(__name__)


@taskiq_broker.task(retry_on_error=True, max_retries=3)
async def sync_book_task(book_id: int) -> None:
    from app.shared.service.infrastructure.dishka.base import get_container
    container = get_container()

    async with container() as request_container:
        book_repository = await request_container.get(BookSQLAlchemyREPO)
        books_elastic_repo = await request_container.get(BooksElasticREPO)
        books_qdrant_collection = await request_container.get(BooksQdrantCollection)
        books_qdrant_repo = await request_container.get(BooksQdrantREPO)

        dtos = await book_repository.get_book_for_sync(book_id)

        if dtos is None:
            # книга удалена из Postgres — подчищаем оба хранилища
            await books_elastic_repo.delete_by_id(book_id)
            await books_qdrant_repo.remove(book_id)
            logger.info("book %s deleted -> removed from ES and Qdrant", book_id)
            return

        qdrant_dto, elastic_dto = dtos

        # ES хранит и недоступные книги (фильтр на стороне поиска)
        await books_elastic_repo.index_batch([elastic_dto])

        if qdrant_dto.is_available:
            # upsert: пересчитывает эмбеддинг и обновляет payload
            await books_qdrant_collection.make_index([qdrant_dto])
        else:
            # недоступные книги в рекомендациях не нужны
            await books_qdrant_repo.remove(book_id)

        logger.info(
            "book %s synced (is_available=%s)",
            book_id,
            qdrant_dto.is_available,
        )
