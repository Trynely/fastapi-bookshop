from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.admin.order.filters import (
    OrderStatusFilter,
    PaymentMethodFilter,
    PaymentStatusFilter,
)
from app.order.db.models.order import (
    AddressModel,
    OrderItemModel,
    OrderModel,
    PaymentModel,
)


class OrderAdmin(ModelView, model=OrderModel):
    name = "Order"
    name_plural = "Orders"
    icon = "fa-solid fa-box"
    identity = "order"

    admin_ignored_fields = [
        "items",
        "payment",
    ]

    column_labels = {
        OrderModel.user_id: "user ID",
        OrderModel.address_id: "address ID",
        OrderModel.total_amount: "total",
        OrderModel.created_at: "created at",
        OrderModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        OrderModel.id,
        OrderModel.user_id,
        OrderModel.total_amount,
        OrderModel.status,
        OrderModel.address_id,
        OrderModel.created_at,
        OrderModel.updated_at,
    ]
    column_searchable_list = [
        OrderModel.id,
        OrderModel.user_id,
    ]
    column_sortable_list = [
        OrderModel.total_amount,
        OrderModel.created_at,
    ]
    column_filters = [OrderStatusFilter()]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_exclude_list = [
        OrderModel.items,
        OrderModel.payment,
    ]

    # form
    form_columns = [
        OrderModel.total_amount,
        OrderModel.status,
        OrderModel.user,
        OrderModel.address,
    ]

    form_ajax_refs = {
        "user": {
            "fields": ("email",),
            "order_by": "id",
            "limit": 5,
        },
        "address": {
            "fields": ("city", "street"),
            "order_by": "id",
            "limit": 5,
        },
    }


class OrderItemAdmin(ModelView, model=OrderItemModel):
    name = "Order Item"
    name_plural = "Order Items"
    icon = "fa-solid fa-boxes-stacked"
    identity = "order_item"

    admin_ignored_fields = []

    column_labels = {
        OrderItemModel.order_id: "order ID",
        OrderItemModel.book_id: "book ID",
        OrderItemModel.created_at: "created at",
        OrderItemModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        OrderItemModel.id,
        OrderItemModel.order_id,
        OrderItemModel.book_id,
        OrderItemModel.quantity,
        OrderItemModel.price,
        OrderItemModel.created_at,
        OrderItemModel.updated_at,
    ]
    column_searchable_list = [
        OrderItemModel.id,
        OrderItemModel.order_id,
        OrderItemModel.book_id,
    ]
    column_sortable_list = [
        OrderItemModel.quantity,
        OrderItemModel.price,
        OrderItemModel.created_at,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # form
    form_columns = [
        OrderItemModel.quantity,
        OrderItemModel.price,
        OrderItemModel.order,
        OrderItemModel.book,
    ]

    form_ajax_refs = {
        "order": {
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


class PaymentAdmin(ModelView, model=PaymentModel):
    name = "Payment"
    name_plural = "Payments"
    icon = "fa-solid fa-credit-card"
    identity = "payment"

    admin_ignored_fields = []

    column_labels = {
        PaymentModel.order_id: "order ID",
        PaymentModel.transaction_id: "transaction ID",
        PaymentModel.created_at: "created at",
        PaymentModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        PaymentModel.id,
        PaymentModel.order_id,
        PaymentModel.amount,
        PaymentModel.method,
        PaymentModel.status,
        PaymentModel.transaction_id,
        PaymentModel.created_at,
        PaymentModel.updated_at,
    ]
    column_searchable_list = [
        PaymentModel.id,
        PaymentModel.order_id,
        PaymentModel.transaction_id,
    ]
    column_sortable_list = [
        PaymentModel.amount,
        PaymentModel.created_at,
    ]
    column_filters = [
        PaymentStatusFilter(),
        PaymentMethodFilter(),
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # form
    form_columns = [
        PaymentModel.amount,
        PaymentModel.method,
        PaymentModel.status,
        PaymentModel.transaction_id,
        PaymentModel.order,
    ]

    form_ajax_refs = {
        "order": {
            "fields": ("id",),
            "order_by": "id",
            "limit": 5,
        },
    }


class AddressAdmin(ModelView, model=AddressModel):
    name = "Address"
    name_plural = "Addresses"
    icon = "fa-solid fa-location-dot"
    identity = "address"

    admin_ignored_fields = [
        "orders",
    ]

    column_labels = {
        AddressModel.user_id: "user ID",
        AddressModel.postal_code: "postal code",
        AddressModel.created_at: "created at",
        AddressModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        AddressModel.id,
        AddressModel.user_id,
        AddressModel.country,
        AddressModel.city,
        AddressModel.street,
        AddressModel.postal_code,
        AddressModel.created_at,
        AddressModel.updated_at,
    ]
    column_searchable_list = [
        AddressModel.id,
        AddressModel.user_id,
        AddressModel.city,
        AddressModel.street,
    ]
    column_sortable_list = [
        AddressModel.country,
        AddressModel.city,
        AddressModel.created_at,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_exclude_list = [
        AddressModel.orders,
    ]

    # form
    form_columns = [
        AddressModel.city,
        AddressModel.street,
        AddressModel.country,
        AddressModel.postal_code,
        AddressModel.user,
    ]

    form_ajax_refs = {
        "user": {
            "fields": ("email",),
            "order_by": "id",
            "limit": 5,
        },
    }
