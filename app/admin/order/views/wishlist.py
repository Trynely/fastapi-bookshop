from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.order.db.models.wishlist import WishlistModel


class WishlistAdmin(ModelView, model=WishlistModel):
    name = "Wishlist"
    name_plural = "Wishlists"
    icon = "fa-solid fa-heart"
    identity = "wishlist"

    admin_ignored_fields = []

    column_labels = {
        WishlistModel.user_id: "user ID",
        WishlistModel.book_id: "book ID",
        WishlistModel.created_at: "created at",
        WishlistModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        WishlistModel.user_id,
        WishlistModel.book_id,
        WishlistModel.created_at,
        WishlistModel.updated_at,
    ]
    column_searchable_list = [
        WishlistModel.user_id,
        WishlistModel.book_id,
    ]
    column_sortable_list = [
        WishlistModel.created_at,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # form
    form_columns = [
        WishlistModel.user_id,
        WishlistModel.book_id,
    ]

    form_include_pk = True
