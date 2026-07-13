from app.client.db.postgres.models import ClientModel
from app.shared.service.infrastructure.base import is_exists
from app.support.db.sqlalchemy.repositories.manager import ManagerSQLAlchemyRepository
from app.support.exceptions.manager import ManagerNotFound

class ManagerFilterQH:
    def __init__(self, manager_repository: ManagerSQLAlchemyRepository):
        self.manager_repository = manager_repository

    async def get_manager(self, manager_id: int) -> ClientModel:
        return await is_exists(
            self.manager_repository.get_by_id(manager_id=manager_id),
            ManagerNotFound(),
        )