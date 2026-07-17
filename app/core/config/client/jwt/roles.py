AUTHORIZED_USER = "authorized_user"
UNAUTHORIZED_USER = "unauthorized_user"
AUTHORIZED_MANAGER = "authorized_manager"

# ClientRoleENUM.value -> роль в access-токене
_CLIENT_ROLE_TO_JWT_ROLE = {
    "user": AUTHORIZED_USER,
    "manager": AUTHORIZED_MANAGER,
}


def client_role_to_jwt_role(client_role) -> str:
    """Маппинг роли из БД в роль access-токена.

    Принимает ClientRoleENUM или её строковое значение; неизвестные роли
    (например, admin — он в JWT-флоу не участвует) получают роль
    обычного пользователя, чтобы не выдать лишних прав.
    """
    role_value = getattr(client_role, "value", client_role)
    return _CLIENT_ROLE_TO_JWT_ROLE.get(role_value, AUTHORIZED_USER)
