from typing import TYPE_CHECKING, Optional
from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)
from app.core.db.models.mixins import IDMixin, TimestampMixin
from app.core.db.models.base import Base

if TYPE_CHECKING:
    from app.client.db.postgres.models import ClientModel
    from app.product.db.postgres.models.book import BookModel

class ReviewModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "reviews"

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="check_review_rating_range"),
    )

    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[Optional[str]] = mapped_column(Text)

    # foreign keys
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    # ORM relations
    user: Mapped["ClientModel"] = relationship(back_populates="reviews")
    book: Mapped["BookModel"] = relationship(back_populates="reviews")

    def __str__(self):
        return str(f"user_id: {self.user_id}, rating: {self.rating}")