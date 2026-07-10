from app.product.db.elasticsearch.repositories.books import BooksElasticREPO
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker


@taskiq_broker.task(schedule=[{"cron": "*/15 * * * *"}])
async def elastic_index_books_task():
    from app.shared.service.infrastructure.dishka.base import get_container
    container = get_container()

    async with container() as request_container:
        book_repository = await request_container.get(BookSQLAlchemyREPO)
        books_elastic_repo = await request_container.get(BooksElasticREPO)

        documents = await book_repository.get_books_for_elastic_indexing()

        await books_elastic_repo.index_batch(documents)
        # Подчищаем документы удалённых книг
        await books_elastic_repo.delete_missing(
            [document.id for document in documents]
        )
