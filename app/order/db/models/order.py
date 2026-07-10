from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship
)
from app.core.db.models.base import Base
from app.core.db.models.mixins import IDMixin, TimestampMixin
from app.product.db.postgres.models.book import BookModel
from app.support.models import pg_enum

class OrderStatusENUM(str, PyEnum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELED = "canceled"


class OrderItemModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "order_items"

    quantity: Mapped[int] = mapped_column(
        Integer, 
        CheckConstraint("quantity > 0", name="qty_gt_0"),
        default=1, 
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), 
        CheckConstraint("price >= 0", name="price_ge_0"),
    )

    # foreign keys
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), 
        index=True, 
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="RESTRICT"), 
        index=True, 
    )
    
    # ORM relations
    order: Mapped["OrderModel"] = relationship(
        back_populates="items", 
        lazy="raise",
    )
    book: Mapped["BookModel"] = relationship(
        back_populates="order_items", 
        lazy="raise",
    )


class PaymentStatusENUM(str, PyEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class PaymentMethodENUM(str, PyEnum):
    CARD = "card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    OTHER = "other"


class PaymentModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "payments"

    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), 
        CheckConstraint("amount >= 0"),
    )
    method: Mapped[PaymentMethodENUM] = mapped_column(
        pg_enum(PaymentMethodENUM, name="payment_method_enum"),
        nullable=False,
    )
    status: Mapped[PaymentStatusENUM] = mapped_column(
        pg_enum(PaymentStatusENUM, name="payment_status_enum"),
        default=PaymentStatusENUM.PENDING,
        nullable=False,
    )
    transaction_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True
    )
    payment_intent_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
    )

    # foreign keys
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), 
        unique=True,
    )

    # ORM relations
    order: Mapped["OrderModel"] = relationship(
        back_populates="payment", 
        lazy="raise",
    )


class AddressModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "addresses"

    city: Mapped[str] = mapped_column(String(100))
    street: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))

    # foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        index=True,
    )

    # ORM relations
    # Связь с заказами
    orders: Mapped[list["OrderModel"]] = relationship(
        back_populates="address", 
        lazy="raise"
    )

    user: Mapped["ClientModel"] = relationship(
        back_populates="addresses",
        lazy="raise"
    )


class OrderModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "orders"

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), 
        CheckConstraint("total_amount >= 0"),
    )
    status: Mapped[OrderStatusENUM] = mapped_column(
        pg_enum(OrderStatusENUM, name="order_status_enum"),
        default=OrderStatusENUM.PENDING,
        nullable=False,
        index=True,
    )

    # foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    address_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("addresses.id", ondelete="RESTRICT"), 
    )

    # ORM relations
    user: Mapped["ClientModel"] = relationship(
        back_populates="orders", 
        lazy="raise",
    )
    address: Mapped["AddressModel"] = relationship(
        back_populates="orders", 
        lazy="raise",
    )
    items: Mapped[list["OrderItemModel"]] = relationship(
        back_populates="order", 
        cascade="all, delete-orphan", 
        lazy="raise",
    )
    payment: Mapped["PaymentModel"] = relationship(
        back_populates="order",
        lazy="raise",
    )


from app.client.db.postgres.models import ClientModel