from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.order.db.models.cart import CartItemModel, CartModel


class CartAdmin(ModelView, model=CartModel):
    name = "Cart"
    name_plural = "Carts"
    icon = "fa-solid fa-cart-shopping"
    identity = "cart"

    admin_ignored_fields = [
        "items",
    ]

    column_labels = {
        CartModel.user_id: "user ID",
        CartModel.created_at: "created at",
        CartModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        CartModel.id,
        CartModel.user_id,
        CartModel.created_at,
        CartModel.updated_at,
    ]
    column_searchable_list = [
        CartModel.id,
        CartModel.user_id,
    ]
    column_sortable_list = [
        CartModel.id,
        CartModel.created_at,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_exclude_list = [
        CartModel.items,
    ]

    # form
    form_columns = [
        CartModel.user,
    ]

    form_ajax_refs = {
        "user": {
            "fields": ("email",),
            "order_by": "id",
            "limit": 5,
        },
    }


class CartItemAdmin(ModelView, model=CartItemModel):
    name = "Cart Item"
    name_plural = "Cart Items"
    icon = "fa-solid fa-basket-shopping"
    identity = "cart_item"

    admin_ignored_fields = []

    column_labels = {
        CartItemModel.cart_id: "cart ID",
        CartItemModel.book_id: "book ID",
        CartItemModel.created_at: "created at",
        CartItemModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        CartItemModel.id,
        CartItemModel.cart_id,
        CartItemModel.book_id,
        CartItemModel.quantity,
        CartItemModel.created_at,
        CartItemModel.updated_at,
    ]
    column_searchable_list = [
        CartItemModel.id,
        CartItemModel.cart_id,
        CartItemModel.book_id,
    ]
    column_sortable_list = [
        CartItemModel.quantity,
        CartItemModel.created_at,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # form
    form_columns = [
        CartItemModel.quantity,
        CartItemModel.cart,
        CartItemModel.book,
    ]

    form_ajax_refs = {
        "cart": {
            "fields": ("id",),
            "order_by": "id",
            "limit": 5,
        },
        "book": {
            "fields": ("title",),
            "order_by": "id",
            "limit": 5,
        },
    }
