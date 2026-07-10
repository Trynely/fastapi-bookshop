from pydantic import BaseModel

class FilterSimilarBooksREQT(BaseModel):
    book_slug: str
    category_id: int
    author_id: int