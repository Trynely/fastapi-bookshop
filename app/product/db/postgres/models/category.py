from sqlalchemy import String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)
from app.core.db.models.mixins import IDMixin, TimestampMixin
from app.core.db.models.base import Base
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.product.db.postgres.models.book import BookModel

class BookCategoryModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "book_categories"

    slug: Mapped[str] = mapped_column(String(255), unique=True)
    title: Mapped[str] = mapped_column(String(150))
    img: Mapped[Optional[str]] = mapped_column(String(255))
    
    # ORM relations
    books: Mapped[list["BookModel"]] = relationship(
        back_populates="category",
        cascade="save-update, merge",
        passive_deletes=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        return self.title