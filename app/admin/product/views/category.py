from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.product.db.postgres.models.category import BookCategoryModel

class CategoryBookAdmin(ModelView, model=BookCategoryModel):
    name = "Category"
    name_plural = "Categories"
    icon = "fa-solid fa-address-book"
    identity = "book_category"

    admin_ignored_fields = []

    column_labels = {
        BookCategoryModel.created_at: "created at",
        BookCategoryModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        BookCategoryModel.id,
        BookCategoryModel.slug,
        BookCategoryModel.title,
        BookCategoryModel.created_at,
        BookCategoryModel.updated_at,
    ]
    column_searchable_list = [
        BookCategoryModel.id,
        BookCategoryModel.title,
        BookCategoryModel.slug,
    ]
    column_sortable_list = [
        BookCategoryModel.created_at,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_exclude_list = [
        BookCategoryModel.books,
    ]

    # form
    form_columns = [
        BookCategoryModel.slug,
        BookCategoryModel.title,
        BookCategoryModel.img,
    ]

    form_include_pk = True