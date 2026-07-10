from datetime import datetime
from sqladmin import ModelView
from sqladmin.filters import BooleanFilter
from app.admin.column_type_formatters import datetime_format
from app.admin.support.filters import EscalationReasonFilter, MessageSenderFilter
from app.support.models import ChatMessageModel, ChatModel


class ChatAdmin(ModelView, model=ChatModel):
    name = "Chat"
    name_plural = "Chats"
    icon = "fa-solid fa-comments"
    identity = "chat"

    admin_ignored_fields = [
        "messages",
    ]

    column_labels = {
        ChatModel.user_id: "user ID",
        ChatModel.manager_id: "manager ID",
        ChatModel.is_closed: "closed",
        ChatModel.escalation_reason: "escalation reason",
        ChatModel.closed_at: "closed at",
        ChatModel.last_message_at: "last message at",
        ChatModel.created_at: "created at",
        ChatModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        ChatModel.id,
        ChatModel.user_id,
        ChatModel.manager_id,
        ChatModel.is_closed,
        ChatModel.escalation_reason,
        ChatModel.last_message_at,
        ChatModel.created_at,
        ChatModel.updated_at,
    ]
    column_searchable_list = [
        ChatModel.id,
        ChatModel.user_id,
        ChatModel.manager_id,
    ]
    column_sortable_list = [
        ChatModel.last_message_at,
        ChatModel.created_at,
    ]
    column_filters = [
        BooleanFilter(ChatModel.is_closed),
        EscalationReasonFilter(),
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_exclude_list = [
        ChatModel.messages,
    ]

    # form
    form_columns = [
        ChatModel.user,
        ChatModel.manager,
        ChatModel.is_closed,
        ChatModel.escalation_reason,
        ChatModel.closed_at,
    ]

    form_ajax_refs = {
        "user": {
            "fields": ("email",),
            "order_by": "id",
            "limit": 5,
        },
        "manager": {
            "fields": ("email",),
            "order_by": "id",
            "limit": 5,
        },
    }


class ChatMessageAdmin(ModelView, model=ChatMessageModel):
    name = "Chat Message"
    name_plural = "Chat Messages"
    icon = "fa-solid fa-message"
    identity = "chat_message"

    admin_ignored_fields = []

    column_labels = {
        ChatMessageModel.chat_id: "chat ID",
        ChatMessageModel.created_at: "created at",
        ChatMessageModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        ChatMessageModel.id,
        ChatMessageModel.chat_id,
        ChatMessageModel.sender,
        ChatMessageModel.content,
        ChatMessageModel.created_at,
        ChatMessageModel.updated_at,
    ]
    column_formatters = {
        ChatMessageModel.content: lambda m, a: (
            m.content[:50] + "…" if m.content and len(m.content) > 50 else m.content
        )
    }
    column_searchable_list = [
        ChatMessageModel.id,
        ChatMessageModel.chat_id,
        ChatMessageModel.content,
    ]
    column_sortable_list = [
        ChatMessageModel.created_at,
    ]
    column_filters = [MessageSenderFilter()]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # form
    form_columns = [
        ChatMessageModel.chat,
        ChatMessageModel.sender,
        ChatMessageModel.content,
    ]

    form_ajax_refs = {
        "chat": {
            "fields": ("id",),
            "order_by": "id",
            "limit": 5,
        },
    }
