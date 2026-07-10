from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.admin.product.filters import RatingFilter
from app.product.db.postgres.models.review import ReviewModel

class ReviewBookAdmin(ModelView, model=ReviewModel):
    name = "Review"
    name_plural = "Reviews"
    icon = "fa-solid fa-star"
    identity = "book_review"

    admin_ignored_fields = []

    column_labels = {
        ReviewModel.created_at: "created at",
        ReviewModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        ReviewModel.id,
        ReviewModel.user_id,
        ReviewModel.book_id,
        ReviewModel.rating,
        ReviewModel.created_at,
        ReviewModel.updated_at,
    ]
    column_searchable_list = [
        ReviewModel.id,
        ReviewModel.rating,
        ReviewModel.book_id,
        ReviewModel.user_id,
    ]
    column_sortable_list = [
        ReviewModel.rating,
        ReviewModel.created_at,
    ]
    column_filters = [RatingFilter()]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # form
    form_excluded_columns = [
        ReviewModel.book_id,
        ReviewModel.user_id,
        ReviewModel.created_at,
        ReviewModel.updated_at,
    ]

    form_include_pk = True

    form_ajax_refs = {
        "user": {
            "fields": ("email",),
            "order_by": "id",
            "limit": 5,
        },
        "book": {
            "fields": ("title",),
            "order_by": "id",
            "limit": 5,
        },
    }