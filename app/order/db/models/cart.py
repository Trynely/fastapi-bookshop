from sqlalchemy import (
    CheckConstraint,
    SmallInteger,
    UniqueConstraint,
    ForeignKey,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)
from app.client.db.postgres.models import ClientModel
from app.core.db.models.base import Base
from app.core.db.models.mixins import IDMixin, TimestampMixin
from app.product.db.postgres.models.book import BookModel

class CartModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "carts"

    # foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
    )

    # ORM relations
    user: Mapped["ClientModel"] = relationship(back_populates="cart")
    items: Mapped[list["CartItemModel"]] = relationship(
        back_populates="cart",
        cascade="all, delete-orphan",
    )

class CartItemModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "cart_items"

    quantity: Mapped[int] = mapped_column(
        SmallInteger, 
        CheckConstraint("quantity > 0"), 
        default=1,
    )

    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="RESTRICT"))

    __table_args__ = (
        UniqueConstraint("cart_id", "book_id", name="uq_cart_book"),
    )

    cart: Mapped["CartModel"] = relationship(back_populates="items")
    book: Mapped["BookModel"] = relationship()