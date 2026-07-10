from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, text
from sqlalchemy.orm import (
    Mapped, mapped_column,
    relationship, declared_attr
)

if TYPE_CHECKING:
    from app.client.db.postgres.models import ClientModel

class UserRelationMixin:
    _user_id_nullable: bool = False
    _user_id_unique: bool = True
    _user_back_populates: str | None = None

    @declared_attr
    def user_id(cls) -> Mapped[int]:
        return mapped_column(ForeignKey("users.id"), unique=cls._user_id_unique, nullable=cls._user_id_nullable)
    
    @declared_attr
    def user(cls) -> Mapped["ClientModel"]:
        return relationship("ClientModel", back_populates=cls._user_back_populates)
    

class IDMixin:
    id: Mapped[int] = mapped_column(primary_key=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )