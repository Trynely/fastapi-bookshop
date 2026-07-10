from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.db.qdrant.collections.books import BooksQdrantCollection
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker

@taskiq_broker.task
async def qdrant_index_books_task():
    from app.shared.service.infrastructure.dishka.base import get_container
    container = get_container()

    async with container() as request_container:
        book_repository = await request_container.get(BookSQLAlchemyREPO)
        books_qdrant_collection = await request_container.get(BooksQdrantCollection)
        books = await book_repository.get_books_for_indexing()
        
        await books_qdrant_collection.make_index(books)