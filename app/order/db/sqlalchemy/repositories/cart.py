from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from app.order.db.models.cart import CartItemModel, CartModel
from app.product.db.postgres.models.book import BookModel
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO
from sqlalchemy.ext.asyncio import AsyncSession

class CartSQLAlchemyRepository(BaseSQLAlchemyREPO[CartModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=CartModel,
        )

    async def get_by_user_id(self, user_id: int) -> CartModel | None:
        result = await self.session.execute(
            select(self.model)
            .where(self.model.user_id == user_id)
            .options(
                selectinload(self.model.items)
                .selectinload(CartItemModel.book)
                .selectinload(BookModel.author)
            )
        )
        return result.scalar_one_or_none()

    async def clear_by_user_id(self, user_id: int) -> None:
        """Удаляет все позиции из корзины пользователя (саму корзину оставляет)."""
        cart_ids = select(CartModel.id).where(CartModel.user_id == user_id)
        await self.session.execute(
            delete(CartItemModel).where(CartItemModel.cart_id.in_(cart_ids))
        )

    async def remove_items_by_user_and_books(
        self,
        user_id: int,
        book_ids: list[int],
    ) -> None:
        """Удаляет из корзины пользователя только указанные книги."""
        if not book_ids:
            return

        cart_ids = select(CartModel.id).where(CartModel.user_id == user_id)
        await self.session.execute(
            delete(CartItemModel).where(
                CartItemModel.cart_id.in_(cart_ids),
                CartItemModel.book_id.in_(book_ids),
            )
        )


class CartItemSQLAlchemyRepository(BaseSQLAlchemyREPO[CartItemModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=CartItemModel,
        )

    async def get_by_cart_and_book_id(
        self,
        cart_id: int,
        book_id: int,
    ) -> CartItemModel | None:
        result = await self.session.execute(
            select(self.model).where(
                self.model.cart_id == cart_id,
                self.model.book_id == book_id,
            )
        )
        return result.scalar_one_or_none()