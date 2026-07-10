from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.order.db.models.order import (
    OrderItemModel,
    OrderModel,
    OrderStatusENUM,
    PaymentModel,
)
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO


class OrderSQLAlchemyRepository(BaseSQLAlchemyREPO[OrderModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=OrderModel,
        )

    def _detail_query(self):
        return (
            select(self.model)
            .options(
                selectinload(self.model.items)
                .joinedload(OrderItemModel.book),
                joinedload(self.model.payment),
            )
        )

    async def get_by_id_with_items(
        self,
        order_id: int,
    ) -> Optional[OrderModel]:
        stmt = self._detail_query().where(self.model.id == order_id)
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_expired_pending_ids(
        self,
        cutoff: datetime,
        limit: int = 100,
    ) -> list[int]:
        """id PENDING-заказов, созданных раньше cutoff (протухшие)."""
        stmt = (
            select(self.model.id)
            .where(
                self.model.status == OrderStatusENUM.PENDING,
                self.model.created_at < cutoff,
            )
            .order_by(self.model.id)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id_for_user(
        self,
        order_id: int,
        user_id: int,
    ) -> Optional[OrderModel]:
        stmt = self._detail_query().where(
            self.model.id == order_id,
            self.model.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_last_for_user(
        self,
        user_id: int,
    ) -> Optional[OrderModel]:
        stmt = (
            self._detail_query()
            .where(self.model.user_id == user_id)
            .order_by(self.model.id.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_list_for_user(
        self,
        user_id: int,
        status: Optional[OrderStatusENUM] = None,
        limit: int = 10,
    ) -> list[OrderModel]:
        stmt = (
            self._detail_query()
            .where(self.model.user_id == user_id)
            .order_by(self.model.id.desc())
            .limit(limit)
        )

        if status is not None:
            stmt = stmt.where(self.model.status == status)

        result = await self.session.execute(stmt)
        return list(result.unique().scalars().all())


class OrderItemSQLAlchemyRepository(BaseSQLAlchemyREPO[OrderItemModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=OrderItemModel,
        )

    async def get_list_by_order_id(self, order_id: int) -> list[OrderItemModel]:
        stmt = select(self.model).where(self.model.order_id == order_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class PaymentSQLAlchemyRepository(BaseSQLAlchemyREPO[PaymentModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=PaymentModel,
        )

    async def get_by_order_id(self, order_id: int) -> Optional[PaymentModel]:
        stmt = select(self.model).where(self.model.order_id == order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
