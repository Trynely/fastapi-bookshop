from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.product.db.postgres.models.author import AuthorModel

class AuthorAdmin(ModelView, model=AuthorModel):
    name = "Author"
    name_plural = "Authors"
    icon = "fa-solid fa-pen-nib"
    identity = "book_author"

    admin_ignored_fields = []

    column_labels = {
        AuthorModel.created_at: "created at",
        AuthorModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        AuthorModel.id,
        AuthorModel.slug,
        AuthorModel.name,
        AuthorModel.created_at,
        AuthorModel.updated_at,
    ]
    column_formatters = {
        AuthorModel.name: lambda m, _: m.name[:60] if m.name else ""
    }
    column_searchable_list = [
        AuthorModel.id,
        AuthorModel.name,
        AuthorModel.slug,
    ]
    column_sortable_list = [
        AuthorModel.created_at,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_exclude_list = [
        AuthorModel.books,
    ]

    # form
    form_columns = [
        AuthorModel.slug,
        AuthorModel.name,
    ]

    form_include_pk = True