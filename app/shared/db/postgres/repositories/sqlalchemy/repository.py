from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import DeclarativeMeta
from app.core.config.base import get_settings
from typing import (
    List,
    Optional,
    Generic,
    TypeVar,
    Type,
)

settings = get_settings()

TModel = TypeVar("TModel", bound=DeclarativeMeta)

class BaseSQLAlchemyREPO(Generic[TModel]):
    def __init__(self, 
        session: AsyncSession,
        model: Type[TModel],
    ):
        self.session = session
        self.model = model

    async def get_list(self) -> List[TModel]:
        list_obj = select(self.model).order_by(self.model.id)
        result = await self.session.execute(list_obj)
        return result.scalars().all()

    async def get_by_id(self, id: int) -> Optional[TModel]:
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == id
            )
        )
        
        return result.scalar_one_or_none()
    
    async def save(self, new_model: TModel) -> TModel:
        model = await self.session.merge(new_model)

        await self.session.flush()
        await self.session.refresh(model)

        return model

    async def remove(self, model: TModel) -> None:
        await self.session.delete(model)