from pydantic import BaseModel
from app.product.api.responses.book.preview import BooksPreviewRESP
from app.product.db.postgres.models.book import BookModel

class BooksMainRecoRESP(BaseModel):
    books: list[BooksPreviewRESP]
    next_cursor: str | None
 
    @classmethod
    def from_page(
        cls,
        books: list[BookModel],
        next_cursor: str | None,
    ) -> "BooksMainRecoRESP":
        return cls(
            books=[BooksPreviewRESP.from_model(b) for b in books],
            next_cursor=next_cursor,
        )