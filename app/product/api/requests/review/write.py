from typing import Optional
from pydantic import (
    BaseModel,
    field_validator,
)
from app.product.exceptions.review.invalid_rating import ReviewRatingInvalidERR

class ReviewWriteREQT(BaseModel):
    book_id: int
    rating: int
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value):
        if not 1 <= value <= 5:
            raise ReviewRatingInvalidERR()
        return value