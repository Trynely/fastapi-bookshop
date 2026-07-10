from app.order.api.requests.order.create import CreateOrderREQT, OrderItemREQT
from app.order.db.models.order import PaymentMethodENUM
from app.order.db.sqlalchemy.repositories.cart import CartSQLAlchemyRepository
from app.order.dto.order.checkout import CheckoutResultDTO
from app.order.exceptions.order import CartEmptyERR, OrderItemsLimitExceededERR
from app.order.usecase.order.purchase import BuyBooks

MAX_CART_ITEMS = 10

class BuyCart:
    """
    Покупка книг прямо из корзины пользователя.
    Берёт актуальные позиции корзины и переиспользует основной
    checkout-флоу (BuyBooks): резерв, заказ, платёж, Stripe-сессия.
    Корзина очищается позже — при подтверждении оплаты (webhook).
    """

    def __init__(
        self,
        cart_repository: CartSQLAlchemyRepository,
        buy_books: BuyBooks,
    ):
        self.cart_repository = cart_repository
        self.buy_books = buy_books

    async def buy(
        self,
        user_id: int,
        payment_method: PaymentMethodENUM = PaymentMethodENUM.CARD,
    ) -> CheckoutResultDTO:
        cart = await self.cart_repository.get_by_user_id(user_id=user_id)

        if cart is None or not cart.items:
            raise CartEmptyERR()

        if len(cart.items) > MAX_CART_ITEMS:
            raise OrderItemsLimitExceededERR()

        order_data = CreateOrderREQT(
            items=[
                OrderItemREQT(book_id=item.book_id, quantity=item.quantity)
                for item in cart.items
            ]
        )

        return await self.buy_books.buy(
            user_id=user_id,
            order_data=order_data,
            payment_method=payment_method,
        )
