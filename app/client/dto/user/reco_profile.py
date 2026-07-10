from dataclasses import dataclass, field

@dataclass(slots=True)
class UserRecoProfileDTO:
    user_id: int

    top_categories: list[int]
    top_authors: list[int]

    category_scores: dict[int, float]
    author_scores: dict[int, float]

    recent_searches: list[str]
    interacted_books: list[int]

    # Купленные книги — исключаются из персональных рекомендаций
    purchased_books: list[int] = field(default_factory=list)

    vector: list[float] | None = None