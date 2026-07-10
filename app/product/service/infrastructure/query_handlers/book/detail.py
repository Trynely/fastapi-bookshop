from app.product.api.responses.book.detail import BookDetailRESP
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.core.config.product.book.router_cache_keys import BookRoutersCacheKeysCONF, book_router_ttl_cache_conf
from app.shared.db.redis import redis_cache
from app.product.exceptions import BookNotFoundERR
from app.shared.service.infrastructure.base import is_exists

class BookDetailQH:
    def __init__(self, book_repository: BookSQLAlchemyREPO):
        self.book_repository = book_repository

    @redis_cache(
        key_builder=BookRoutersCacheKeysCONF.detail,
        response_model=BookDetailRESP,
        ttl=book_router_ttl_cache_conf.detail_router,
    )
    async def get_book(self, book_slug: str) -> BookDetailRESP:
        book = await is_exists(
            self.book_repository.get_by_slug(book_slug),
            BookNotFoundERR(),
        )

        return BookDetailRESP.model_validate(book)