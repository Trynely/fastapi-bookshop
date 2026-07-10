from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from app.product.db.postgres.models.book import BookModel

class BookBaseRESP(BaseModel):
    id: int
    slug: str
    title: str
    price: Decimal
    quantity: int
    img: Optional[str]
    discount_percent: Optional[int]
    issue_year: Optional[int]
    rating: Optional[float]
    total_sales: Optional[int]
    sum_ratings: Optional[int]
    is_available: bool

    model_config = {
        "from_attributes": True
    }

    @classmethod
    def _extract_common(cls, book: BookModel) -> dict:
        return dict(
            id=book.id,
            slug=book.slug,
            title=book.title,
            price=book.price,
            quantity=book.quantity,
            img=book.img,
            discount_percent=book.discount_percent,
            issue_year=book.issue_year,
            rating=book.rating,
            total_sales=book.total_sales,
            sum_ratings=book.sum_ratings,
            is_available=book.is_available,
        )