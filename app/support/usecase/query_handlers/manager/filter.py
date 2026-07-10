from app.core.config.support.redis.cache.user_schat import user_chat_cache_key
from app.shared.service.infrastructure.base import is_exists
from app.shared.db.redis import redis_cache
from app.support.api.responses.chat import ChatRead
from app.support.db.sqlalchemy.repositories.manager import ManagerSQLAlchemyRepository
from app.support.exceptions.manager import ManagerNotFound
from app.support.models import ChatModel

class ManagerFilterQH:
    def __init__(self, manager_repository: ManagerSQLAlchemyRepository):
        self.manager_repository = manager_repository
    
    async def get_manager(self, manager_id: int) -> ChatModel:
        return await is_exists(
            self.manager_repository.get_by_id(manager_id=manager_id),
            ManagerNotFound(),
        )