from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.client.api.dependencies import auth_manager
from app.client.api.requests.user.auth import UserAuthorizedREQT
from app.client.db.postgres.models import ClientModel, ClientRoleENUM
from app.core.db.postgres import db_helper


async def get_current_manager(
    payload: UserAuthorizedREQT = Depends(auth_manager),
    db: AsyncSession = Depends(db_helper.session_getter),
) -> ClientModel:
    """Двухуровневая проверка менеджера: роль в JWT (auth_manager),
    затем актуальная роль и активность в БД."""
    user = await db.get(ClientModel, int(payload.sub))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.role != ClientRoleENUM.MANAGER or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only managers allowed",
        )

    return user
