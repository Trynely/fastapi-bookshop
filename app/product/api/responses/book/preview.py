from typing import List
from app.product.api.responses.author.detail import AuthorDetailRESP
from app.product.api.responses.book.base import BookBaseRESP
from app.product.db.postgres.models.book import BookModel
from app.shared.api.responses.cursor_pagination import CursorPaginationRESP

class BooksPreviewRESP(BookBaseRESP):
    category: str
    author: AuthorDetailRESP

    @classmethod
    def from_model(cls, book: BookModel) -> "BooksPreviewRESP":
        common = cls._extract_common(book)

        return cls(
            **common,
            category=book.category.title,
            author=AuthorDetailRESP.model_validate(book.author),
        )


class BooksPreviewPaginationRESP(CursorPaginationRESP):
    books: List[BooksPreviewRESP]