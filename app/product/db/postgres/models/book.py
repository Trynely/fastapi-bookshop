from datetime import date
from decimal import Decimal
import random
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    Index,
    String,
    ForeignKey,
    Numeric,
    Integer,
    Text,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)
from app.core.db.models.mixins import IDMixin, TimestampMixin
from app.core.db.models.base import Base
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.client.db.postgres.models import ClientModel
    from app.order.db.models.order import OrderItemModel
    from app.product.db.postgres.models.author import AuthorModel
    from app.product.db.postgres.models.category import BookCategoryModel
    from app.product.db.postgres.models.country import MadeInModel
    from app.product.db.postgres.models.paper import PaperTypeModel
    from app.product.db.postgres.models.review import ReviewModel


class BookPopularityStatsModel(Base, TimestampMixin):
    __tablename__ = "book_popularity_stats"

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stat_date: Mapped[date] = mapped_column(Date, primary_key=True, index=True)

    sales: Mapped[int] = mapped_column(default=0, server_default="0")
    wishlist_adds: Mapped[int] = mapped_column(default=0, server_default="0")
    reviews: Mapped[int] = mapped_column(default=0, server_default="0")
    popularity_score: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        default=0,
        server_default="0",
        index=True,
    )


class BookModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "books"

    __table_args__ = (
        CheckConstraint(
            "price >= 0",
            name="check_price_positive",
        ),
        CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="check_discount_range",
        ),
        CheckConstraint(
            "pages >= 0",
            name="check_pages_positive",
        ),
        CheckConstraint(
            "quantity >= 0",
            name="check_quantity_positive",
        ),
        CheckConstraint(
            "rating >= 0 AND rating <= 5",
            name="check_rating_range",
        ),

        Index(
            "ix_books_random_key",
            "random_key",
        ),

        Index(
            "ix_books_available_random_key",
            "is_available",
            "random_key",
        ),
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
    )

    title: Mapped[str] = mapped_column(String(255))

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
    )

    pages: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    img: Mapped[Optional[str]] = mapped_column(
        String(255),
    )

    discount_percent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
    )

    issue_year: Mapped[Optional[int]] = mapped_column(
        Integer,
    )

    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("0.00"),
        server_default="0.00",
    )

    total_ratings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default="0",
    )

    sum_ratings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default="0",
    )

    total_sales: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default="0",
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )

    random_key: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=lambda: random.getrandbits(63),
        server_default=text(
            "(floor(random() * 9223372036854775807))::bigint"
        ),
    )

    # foreign keys

    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "book_categories.id",
            ondelete="RESTRICT",
        ),
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey(
            "authors.id",
            ondelete="RESTRICT",
        ),
    )

    paper_type_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "paper_types.id",
            ondelete="SET NULL",
        ),
    )

    made_in_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey(
            "countries.id",
            ondelete="SET NULL",
        ),
    )

    author: Mapped["AuthorModel"] = relationship(
        back_populates="books",
        lazy="raise",
    )

    category: Mapped["BookCategoryModel"] = relationship(
        back_populates="books",
        lazy="raise",
    )

    paper_type: Mapped["PaperTypeModel"] = relationship(
        back_populates="books",
        lazy="raise",
    )

    made_in: Mapped["MadeInModel"] = relationship(
        back_populates="books",
        lazy="raise",
    )

    reviews: Mapped[list["ReviewModel"]] = relationship(
        back_populates="book",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    order_items: Mapped[list["OrderItemModel"]] = relationship(
        back_populates="book",
        lazy="raise",
    )

    wishlisted_by: Mapped[list["ClientModel"]] = relationship(
        secondary="wishlists",
        back_populates="wishlist",
        lazy="raise",
    )

    def __str__(self) -> str:
        return self.title