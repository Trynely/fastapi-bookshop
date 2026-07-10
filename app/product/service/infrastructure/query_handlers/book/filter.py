from app.product.api.responses.book.preview import BooksPreviewPaginationRESP, BooksPreviewRESP
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.core.config.product.book.router_cache_keys import BookRoutersCacheKeysCONF, book_router_ttl_cache_conf
from app.shared.db.redis import redis_cache
from app.shared.api.requests.cursor_pagintaion import (
    CursorEncodedPaginationREQT,
    CursorMD5RandomPaginationREQT,
    CursorIDPaginationREQT,
)
from typing import Optional

class BookFilterQH:
    def __init__(self, book_repository: BookSQLAlchemyREPO):
        self.book_repository = book_repository
    
    @redis_cache(
        key_builder=BookRoutersCacheKeysCONF.by_new,
        response_model=BooksPreviewPaginationRESP,
        ttl=book_router_ttl_cache_conf.by_new_router,
    )
    async def by_new(
        self,
        pagination: Optional[CursorIDPaginationREQT] = None,
    ) -> BooksPreviewPaginationRESP:
        result = await self.book_repository.get_list_by_new(pagination=pagination)

        return BooksPreviewPaginationRESP(
            books=[BooksPreviewRESP.from_model(book) for book in result.items],
            next=result.next_cursor,
            has_next=result.has_more,
        )
    
    @redis_cache(
        key_builder=BookRoutersCacheKeysCONF.by_popular,
        response_model=BooksPreviewPaginationRESP,
        ttl=book_router_ttl_cache_conf.by_popular_router,
    )
    async def by_popular(
        self,
        pagination: Optional[CursorEncodedPaginationREQT] = None,
    ) -> BooksPreviewPaginationRESP:
        result = await self.book_repository.get_list_by_popular(
            pagination=pagination
        )
        return BooksPreviewPaginationRESP(
            books=[BooksPreviewRESP.from_model(book) for book in result.items],
            next=result.next_cursor,
            has_next=result.has_more,
        )
        
    async def by_category(
        self,
        category_slug: str,
        random_pagination: CursorMD5RandomPaginationREQT,
    ) -> BooksPreviewPaginationRESP:
        books = await self.book_repository.get_list_by_category_slug(
            category_slug=category_slug,
            random_pagination=random_pagination,
        )
    
        return BooksPreviewPaginationRESP(
            books=[BooksPreviewRESP.from_model(book) for book in books.items],
            next=books.next_cursor,
            has_next=books.has_more,
        )