from collections.abc import Iterable
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.client.db.postgres.models import UserEventENUM, UserEventModel
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO

MAX_EVENTS = 200

class UserEventSQLAlchemyREPO(BaseSQLAlchemyREPO[UserEventModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=UserEventModel,
        )

    async def get_list_by_user_id_by_new(
        self,
        user_id: int,
    ) -> list[UserEventModel]:
        result = await self.session.execute(
            select(self.model).where(
                self.model.user_id == user_id
            ).order_by(
                self.model.created_at.desc()
            ).limit(MAX_EVENTS)
        )

        return result.scalars().all()

    async def get_by_user_id_and_event_type(
        self,
        user_id: int,
        event_type: UserEventENUM,
    ) -> list[UserEventModel]:
        result = await self.session.execute(
            select(self.model).where(
                self.model.user_id == user_id,
                self.model.event_type == event_type,
            )
        )

        return result.scalars().all()

    async def get_last_user_event(
        self,
        user_id: int,
    ) -> Optional[UserEventModel]:
        result = await self.session.execute(
            select(self.model)
            .where(
                self.model.user_id == user_id,
            )
            .order_by(self.model.created_at.desc())
            .limit(1)
        )

        return result.scalar_one_or_none()
    
    async def get_weights_by_book(
        self,
        user_id: int,
        book_ids: list[int],
    ) -> dict[int, float]:
        user_book_events = await self.session.execute(
            select(
                self.model.book_id,
                func.sum(self.model.weight).label("total_weight"),
            )
            .where(
                self.model.user_id == user_id,
                self.model.book_id.in_(book_ids),
            )
            .group_by(self.model.book_id)
        )

        return user_book_events.all()
    
    async def get_weights_by_users_and_books(
        self,
        user_ids: Iterable[int],
        exclude_book_ids: list[int] | None = None,
    ) -> list[tuple[int, int, float]]:
        exclude_book_ids = exclude_book_ids or []

        query = (
            select(
                self.model.user_id,
                self.model.book_id,
                func.sum(self.model.weight).label("total_weight"),
            )
            .where(
                self.model.user_id.in_(user_ids),
                self.model.book_id.isnot(None),
            )
            .group_by(
                self.model.user_id,
                self.model.book_id,
            )
        )

        if exclude_book_ids:
            query = query.where(
                self.model.book_id.notin_(exclude_book_ids),
            )

        result = await self.session.execute(query)
        return result.all()