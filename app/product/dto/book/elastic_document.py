from dataclasses import dataclass


@dataclass(slots=True)
class BookElasticDocumentDTO:
    id: int
    title: str

    author_id: int
    author_name: str

    category_id: int
    category_slug: str
    category_name: str

    country: str | None

    issue_year: int | None
    rating: float

    is_available: bool
