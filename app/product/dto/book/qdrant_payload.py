from dataclasses import dataclass

@dataclass(slots=True)
class BooksQdrantPayloadDTO:
    id: int
    title: str
    description: str | None

    author_id: int
    author_name: str

    category_id: int
    category_name: str

    issue_year: int | None
    rating: float

    is_available: bool