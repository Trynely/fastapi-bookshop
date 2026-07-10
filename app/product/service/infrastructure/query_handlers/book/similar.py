from app.product.api.requests.filter_by_similar import FilterSimilarBooksREQT
from app.product.api.responses.book.preview import BooksPreviewPaginationRESP, BooksPreviewRESP
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.shared.api.requests.cursor_pagintaion import CursorMD5RandomPaginationREQT

class BookSimilarQH:
    def __init__(self, book_repository: BookSQLAlchemyREPO):
        self.book_repository = book_repository

    async def by_category_and_author(
        self,
        similar: FilterSimilarBooksREQT,
        random_pagination: CursorMD5RandomPaginationREQT,
    ) -> BooksPreviewPaginationRESP:
        books = await self.book_repository.get_similar_list_by_category_and_author_id(
            similar=similar,
            random_pagination=random_pagination,
        )

        return BooksPreviewPaginationRESP(
            books=[BooksPreviewRESP.from_model(book) for book in books.items],
            next=books.next_cursor,
            has_next=books.has_more,
        )