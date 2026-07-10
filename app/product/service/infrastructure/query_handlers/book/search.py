from typing import Optional

from app.product.api.requests.filter_by_category import (
    CategoryBooksByAuthorNameREQT,
    CategoryBooksByCountryREQT,
    CategoryBooksByTitleREQT,
)
from app.product.api.responses.book.preview import (
    BooksPreviewPaginationRESP,
    BooksPreviewRESP,
)
from app.product.db.elasticsearch.repositories.books import (
    AUTHOR_NAME_FIELD,
    COUNTRY_FIELD,
    TITLE_FIELD,
    BooksElasticREPO,
)
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.shared.api.requests.cursor_pagintaion import CursorEncodedPaginationREQT


class CategoryBooksSearchQH:
    """
    Поиск книг категории через Elasticsearch:
    ES отдаёт id книг по релевантности, Postgres гидрирует модели.
    """

    def __init__(
        self,
        books_elastic_repo: BooksElasticREPO,
        book_repository: BookSQLAlchemyREPO,
    ):
        self.books_elastic_repo = books_elastic_repo
        self.book_repository = book_repository

    async def by_author(
        self,
        filters: CategoryBooksByAuthorNameREQT,
        pagination: Optional[CursorEncodedPaginationREQT] = None,
    ) -> BooksPreviewPaginationRESP:
        return await self._search(
            category_slug=filters.category_slug,
            field=AUTHOR_NAME_FIELD,
            query=filters.name,
            pagination=pagination,
        )

    async def by_title(
        self,
        filters: CategoryBooksByTitleREQT,
        pagination: Optional[CursorEncodedPaginationREQT] = None,
    ) -> BooksPreviewPaginationRESP:
        return await self._search(
            category_slug=filters.category_slug,
            field=TITLE_FIELD,
            query=filters.title,
            pagination=pagination,
        )

    async def by_country(
        self,
        filters: CategoryBooksByCountryREQT,
        pagination: Optional[CursorEncodedPaginationREQT] = None,
    ) -> BooksPreviewPaginationRESP:
        return await self._search(
            category_slug=filters.category_slug,
            field=COUNTRY_FIELD,
            query=filters.made_in,
            pagination=pagination,
        )

    async def _search(
        self,
        category_slug: str,
        field: str,
        query: str,
        pagination: Optional[CursorEncodedPaginationREQT] = None,
    ) -> BooksPreviewPaginationRESP:
        page = await self.books_elastic_repo.search_ids_in_category(
            category_slug=category_slug,
            field=field,
            query=query,
            encoded_cursor=pagination.encoded_cursor if pagination else None,
        )

        books = await self.book_repository.get_list_by_ids(page.items)

        # Восстанавливаем порядок релевантности из Elasticsearch
        books_by_id = {book.id: book for book in books}
        ordered_books = [
            books_by_id[book_id]
            for book_id in page.items
            if book_id in books_by_id
        ]

        return BooksPreviewPaginationRESP(
            books=[BooksPreviewRESP.from_model(book) for book in ordered_books],
            next=page.next_cursor,
            has_next=page.has_more,
        )
