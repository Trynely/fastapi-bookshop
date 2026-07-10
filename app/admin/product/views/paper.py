from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.product.db.postgres.models.paper import PaperTypeModel

class PaperBookAdmin(ModelView, model=PaperTypeModel):
    name = "Paper"
    name_plural = "Papers"
    icon = "fa-solid fa-file"
    identity = "book_paper"

    admin_ignored_fields = []

    column_labels = {
        PaperTypeModel.created_at: "created at",
        PaperTypeModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        PaperTypeModel.id,
        PaperTypeModel.type_name,
        PaperTypeModel.created_at,
        PaperTypeModel.updated_at,
    ]
    column_searchable_list = [
        PaperTypeModel.id,
        PaperTypeModel.type_name,
    ]
    column_sortable_list = [
        PaperTypeModel.created_at,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_exclude_list = [
        PaperTypeModel.books,
    ]

    # form
    form_columns = [
        PaperTypeModel.type_name,
    ]

    form_include_pk = True