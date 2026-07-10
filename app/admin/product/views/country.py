from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.product.db.postgres.models.country import MadeInModel

class MadeInBookAdmin(ModelView, model=MadeInModel):
    name = "Made In"
    name_plural = "Countries"
    icon = "fa-solid fa-flag"
    identity = "book_country"

    admin_ignored_fields = []

    column_labels = {
        MadeInModel.created_at: "created at",
        MadeInModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        MadeInModel.id,
        MadeInModel.slug,
        MadeInModel.country,
        MadeInModel.created_at,
        MadeInModel.updated_at,
    ]
    column_searchable_list = [
        MadeInModel.id,
        MadeInModel.slug,
        MadeInModel.country,
    ]
    column_sortable_list = [
        MadeInModel.created_at,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_exclude_list = [
        MadeInModel.books,
    ]

    # form
    form_columns = [
        MadeInModel.slug,
        MadeInModel.country,
    ]

    form_include_pk = True