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


class PaperTypeModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "paper_types"

    type_name: Mapped[str] = mapped_column(String(255), unique=True)

    # ORM relations
    books: Mapped[List["BookModel"]] = relationship("BookModel", back_populates="paper_type")

    def __str__(self) -> str:
        return self.type_name