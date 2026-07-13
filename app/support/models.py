from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Text,
    CheckConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.models.base import Base
from app.core.db.models.mixins import IDMixin, TimestampMixin

class ChatMessageSender(str, Enum):
    USER = "user"
    BOT = "bot"
    MANAGER = "manager"


class EscalationReason(str, Enum):
    OPERATOR_REQUEST = "operator_request"
    COMPLEX_CASE = "complex_case"
    PROFANITY = "profanity"


def pg_enum(enum_cls, name: str):
    return PgEnum(
        enum_cls,
        name=name,
        values_callable=lambda e: [i.value for i in e],
        native_enum=True,
    )


class ChatModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "chats"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
    )

    escalation_reason: Mapped[EscalationReason | None] = mapped_column(
        pg_enum(EscalationReason, "escalationreason"),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        index=True,
    )

    user = relationship("ClientModel", foreign_keys=[user_id], back_populates="chats")
    manager = relationship("ClientModel", foreign_keys=[manager_id], back_populates="managed_chats")

    messages = relationship(
        "ChatMessageModel",
        back_populates="chat",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ChatMessageModel.created_at",
    )

    __table_args__ = (
        CheckConstraint(
            "(is_closed = false) OR (closed_at IS NOT NULL)",
            name="closed_at_required_if_closed",
        ),
    )


Index(
    "unique_active_chat_per_user",
    ChatModel.user_id,
    unique=True,
    postgresql_where=ChatModel.is_closed.is_(False),
)

Index(
    "ix_chat_escalation_queue",
    ChatModel.is_closed,
    ChatModel.escalation_reason,
    ChatModel.manager_id,
    ChatModel.last_message_at
)


class ChatMessageModel(Base, IDMixin, TimestampMixin):
    __tablename__ = "chat_messages"

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    sender: Mapped[ChatMessageSender] = mapped_column(
        pg_enum(ChatMessageSender, "messagesender"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    chat: Mapped["ChatModel"] = relationship("ChatModel", back_populates="messages")