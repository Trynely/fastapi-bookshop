from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.client.db.postgres.models import UserEventENUM, UserEventModel


class UserEventTypeFilter:
    title = "Event Type"
    parameter_name = "event_type"

    def lookups(self, request, model, run_query) -> list[tuple[str, str]]:
        return [
            (event.value, event.value.replace("_", " ").capitalize())
            for event in UserEventENUM
        ]

    async def get_filtered_query(self, stmt, value, model):
        if value:
            stmt = stmt.where(model.event_type == value)

        return stmt


class UserEventAdmin(ModelView, model=UserEventModel):
    name = "User Event"
    name_plural = "User Events"
    icon = "fa-solid fa-chart-line"
    identity = "user_event"

    # лог — только чтение
    can_create = False
    can_edit = False

    admin_ignored_fields = []

    column_labels = {
        UserEventModel.user_id: "user ID",
        UserEventModel.book_id: "book ID",
        UserEventModel.event_type: "event type",
        UserEventModel.category_id: "category ID",
        UserEventModel.author_id: "author ID",
        UserEventModel.metada: "metadata",
        UserEventModel.created_at: "created at",
        UserEventModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        UserEventModel.id,
        UserEventModel.user_id,
        UserEventModel.book_id,
        UserEventModel.event_type,
        UserEventModel.weight,
        UserEventModel.created_at,
    ]
    column_searchable_list = [
        UserEventModel.id,
        UserEventModel.user_id,
        UserEventModel.book_id,
    ]
    column_sortable_list = [
        UserEventModel.weight,
        UserEventModel.created_at,
    ]
    column_filters = [UserEventTypeFilter()]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_list = [
        UserEventModel.id,
        UserEventModel.user_id,
        UserEventModel.book_id,
        UserEventModel.event_type,
        UserEventModel.metada,
        UserEventModel.category_id,
        UserEventModel.author_id,
        UserEventModel.weight,
        UserEventModel.created_at,
        UserEventModel.updated_at,
    ]
