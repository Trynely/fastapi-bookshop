from enum import Enum as PyEnum
from app.core.db.models.base import Base
from app.core.db.models.mixins import IDMixin, TimestampMixin
from sqlalchemy.orm import (
    Mapped, mapped_column,
    relationship
)
from sqlalchemy import String, Boolean
from app.product.db.postgres.models.book import BookModel
from app.product.db.postgres.models.review import ReviewModel
from app.support.models import pg_enum

class ClientRoleENUM(str, PyEnum):
    USER = "user"
    MANAGER = "manager"
    ADMIN = "admin"


class OAuthProviderENUM(str, PyEnum):
    GOOGLE = "google"
    GITHUB = "github"


class ClientModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    oauth_provider: Mapped[OAuthProviderENUM | None] = mapped_column(
        pg_enum(OAuthProviderENUM, name="oauth_provider_enum"),
        nullable=True,
        index=True,
    )
    oauth_id: Mapped[str | None] = mapped_column(
        nullable=True,
        unique=True,
        index=True,
    )
    role: Mapped[ClientRoleENUM] = mapped_column(
        pg_enum(ClientRoleENUM, name="client_role_enum"),
        default=ClientRoleENUM.USER,
        nullable=False,
        index=True,
    )

    # ORM relations
    reviews: Mapped[list["ReviewModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    cart: Mapped["CartModel"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="noload",
    )
    wishlist: Mapped[list["BookModel"]] = relationship(
        secondary="wishlists", 
        back_populates="wishlisted_by",
        lazy="noload",
    )
    orders: Mapped[list["OrderModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    addresses: Mapped[list["AddressModel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    chats: Mapped[list["ChatModel"]] = relationship(
        "ChatModel",
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="ChatModel.user_id",
    )
    managed_chats: Mapped[list["ChatModel"]] = relationship(
        "ChatModel",
        back_populates="manager",
        foreign_keys="ChatModel.manager_id",
    )

    def __str__(self) -> str:
        return self.email

from app.order.db.models.cart import CartModel
from app.order.db.models.order import AddressModel, OrderModel
from app.support.models import ChatModel


# app/recommendations/models.py
from enum import Enum as PyEnum
from sqlalchemy import (
    BigInteger, String, Integer, JSON, 
    ForeignKey, Index, Float
)
from sqlalchemy.orm import Mapped, mapped_column


class UserEventENUM(str, PyEnum):
    VIEW          = "view"
    SEARCH        = "search"
    WISHLIST_ADD  = "wishlist_add"
    WISHLIST_DEL  = "wishlist_remove"
    CART_ADD      = "cart_add"
    CART_REMOVE   = "cart_remove"
    PURCHASE      = "purchase"
    RATING        = "rating"
    SHARE         = "share"
    PREVIEW       = "preview"


USER_EVENT_WEIGHTS: dict[UserEventENUM, float] = {
    UserEventENUM.VIEW:         0.5,
    UserEventENUM.SEARCH:       0.3,
    UserEventENUM.WISHLIST_ADD: 1.5,
    UserEventENUM.WISHLIST_DEL: -0.5,
    UserEventENUM.CART_ADD:     2.0,
    UserEventENUM.CART_REMOVE:  -0.3,
    UserEventENUM.PURCHASE:     3.0,
    UserEventENUM.RATING:       0.0,   # рассчитывается отдельно
    UserEventENUM.SHARE:        1.2,
    UserEventENUM.PREVIEW:      0.8,
}


class UserEventModel(Base, IDMixin, TimestampMixin):
    """Лог всех пользовательских действий."""
    __tablename__ = "user_events"
    
    __table_args__ = (
        Index("ix_user_events_user_book", "user_id", "book_id"),
        Index("ix_user_events_user_type", "user_id", "event_type"),
        Index("ix_user_events_created", "created_at"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    book_id: Mapped[int | None] = mapped_column(
        ForeignKey("books.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[UserEventENUM] = mapped_column(
        pg_enum(UserEventENUM, name="user_event_enum"),
        nullable=False,
    )
    # гибкое поле: rating value, search query, session_id и т.д.
    metada: Mapped[dict] = mapped_column(JSON, default=dict)
    # денормализация для аналитики без JOIN
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    author_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[float] = mapped_column(Float, default=0.5)