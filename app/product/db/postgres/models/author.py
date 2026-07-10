from sqlalchemy import String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)
from app.core.db.models.mixins import IDMixin, TimestampMixin
from app.core.db.models.base import Base
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.product.db.postgres.models.book import BookModel


class AuthorModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "authors"

    slug: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)

    # ORM relations
    books: Mapped[List["BookModel"]] = relationship("BookModel", back_populates="author", lazy="selectin")

    def __str__(self) -> str:
        return self.name