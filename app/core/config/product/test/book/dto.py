from dataclasses import dataclass, field
from datetime import timezone, datetime
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True, slots=True)
class BookDTOTestConf:
    slug: str = "clean-architecture"
    title: str = "Clean Architecture"
    price: Decimal = Decimal("39.99")
    pages: int = 432
    quantity: int = 10

    img: Optional[str] = "books/clean-architecture.jpg"
    discount_percent: Optional[int] = 10
    description: Optional[str] = (
        "A Craftsman's Guide to Software Structure and Design"
    )
    issue_year: Optional[int] = 2017

    rating: float = 4.7
    total_ratings: int = 1240
    sum_ratings: int = 5828
    total_sales: int = 860
    is_available: bool = True

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

book_dto_test_conf = BookDTOTestConf()