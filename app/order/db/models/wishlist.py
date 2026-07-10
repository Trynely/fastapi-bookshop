from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db.models.base import Base
from app.core.db.models.mixins import TimestampMixin

class WishlistModel(Base, TimestampMixin):
    __tablename__ = "wishlists"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True,
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), 
        primary_key=True,
    )