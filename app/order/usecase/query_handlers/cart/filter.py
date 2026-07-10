from app.order.api.responses.cart.base import CartResponse
from app.order.db.sqlalchemy.repositories.cart import CartSQLAlchemyRepository

class CartFilterQH:
    def __init__(self, cart_repository: CartSQLAlchemyRepository):
        self.cart_repository = cart_repository

    async def get_cart_items_by_user(self, user_id: int) -> CartResponse:
        user_cart = await self.cart_repository.get_by_user_id(user_id)

        if user_cart is None:
            return CartResponse(items=[])
        return CartResponse.model_validate(user_cart)