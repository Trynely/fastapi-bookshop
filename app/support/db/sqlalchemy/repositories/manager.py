from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO
from app.client.db.postgres.models import ClientModel, ClientRoleENUM

class ManagerSQLAlchemyRepository(BaseSQLAlchemyREPO[ClientModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=ClientModel
        )

    async def get_by_id(self, manager_id: int) -> Optional[ClientModel]:
        stmt = select(ClientModel).where(
            ClientModel.id == manager_id,
            ClientModel.role == ClientRoleENUM.MANAGER
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()