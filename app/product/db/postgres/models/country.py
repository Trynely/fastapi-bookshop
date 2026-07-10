from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)
from app.core.db.models.mixins import IDMixin, TimestampMixin
from app.core.db.models.base import Base

if TYPE_CHECKING:
    from app.product.db.postgres.models.book import BookModel

class MadeInModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "countries"

    slug: Mapped[str] = mapped_column(String(255), unique=True)
    country: Mapped[str] = mapped_column(String(60), unique=True)

    # ORM relations
    books: Mapped[list["BookModel"]] = relationship(back_populates="made_in")

    def __str__(self) -> str:
        return self.country