from datetime import datetime
from sqladmin import ModelView
from sqladmin.filters import BooleanFilter, OperationColumnFilter
from app.admin.client.filters import ClientRoleFilterAdmin, OauthProviderFilterAdmin
from app.admin.column_type_formatters import datetime_format
from app.client.db.postgres.models import ClientModel

class ClientAdmin(ModelView, model=ClientModel):
    name = "Client"
    name_plural = "Clients"
    icon = "fa-solid fa-user"
    identity = "client"

    column_labels = {
        ClientModel.is_active: "is active",
        ClientModel.role: "role",
        ClientModel.created_at: "created at",
        ClientModel.updated_at: "updated at"
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        ClientModel.id,
        ClientModel.email,
        ClientModel.username,
        ClientModel.oauth_provider,
        ClientModel.is_active,
        ClientModel.role,
        ClientModel.created_at,
        ClientModel.updated_at,
    ]
    column_formatters = {
        ClientModel.username: lambda m, a: m.username[:10] if m.username else ""
    }
    column_searchable_list = [ClientModel.id, ClientModel.email]
    column_sortable_list = [ClientModel.id, ClientModel.created_at]
    column_filters = [
        OauthProviderFilterAdmin(),
        ClientRoleFilterAdmin(),
        BooleanFilter(ClientModel.is_active),
        OperationColumnFilter(ClientModel.email),
    ]
    
    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_list = [
        ClientModel.id,
        ClientModel.email,
        ClientModel.username,
        ClientModel.is_active,
        ClientModel.role,
        ClientModel.oauth_provider,
        ClientModel.oauth_id,
        ClientModel.created_at,
        ClientModel.updated_at,
    ]

    # form
    form_columns = [
        ClientModel.email,
        ClientModel.username,
        ClientModel.password,
        ClientModel.role,
        ClientModel.is_active,
        ClientModel.reviews
    ]
    form_ajax_refs = {
        "reviews": {
            "fields": ("id",),
            "order_by": "id",
        }
    }

    form_create_rules = [
        "email",
        "username",
        "password",
        "role",
        "is_active",
    ]
    form_edit_rules = [
        "username",
        "role",
        "is_active",
    ]