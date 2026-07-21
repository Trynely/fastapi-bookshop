from fastapi import (
    APIRouter,
    Depends,
    Query,
    status,
)
from app.client.api.events.user.personal_reco import UserPersonalRecoEVENT
from app.client.api.requests.user.auth import UserAuthorizedREQT
from app.client.db.postgres.models import UserEventENUM
from app.client.service.infrastructure.rabbitmq.producer.reco_events import publish_user_personal_books_reco_rmq_safe
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.core.db.postgres import SessionDependency
from app.order.db.sqlalchemy.repositories.cart import CartItemSQLAlchemyRepository, CartSQLAlchemyRepository
from app.order.usecase.cart.add_item import AddBookToCart
from app.order.usecase.cart.set_quantity import SetCartItemQuantity
from app.order.usecase.query_handlers.cart.filter import CartFilterQH
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.client.api.dependencies import auth_client

cart_router = APIRouter(prefix="/cart", tags=["🧺 Корзина"])

@cart_router.get(
    "/by/user",
    summary="Список книг пользователя",
    status_code=status.HTTP_200_OK,
)
async def cart_user_booklist_router(
    session: SessionDependency,
    user: UserAuthorizedREQT = Depends(auth_client),
):
    repo = CartSQLAlchemyRepository(session)
    query = CartFilterQH(cart_repository=repo)

    return await query.get_cart_items_by_user(user_id=user.sub)


@cart_router.post(
    "",
    summary="Добавить В Корзину",
    status_code=status.HTTP_201_CREATED,
)
async def add_item_to_cart_router(
    session: SessionDependency,
    book_id: int,
    user: UserAuthorizedREQT = Depends(auth_client),
):
    cart_book = AddBookToCart(
        transaction=SQLAlchemyTransaction(session),
        book_repository=BookSQLAlchemyREPO(session),
        cart_repository=CartSQLAlchemyRepository(session),
        cart_item_repository=CartItemSQLAlchemyRepository(session),
    )
    await cart_book.add(user_id=user.sub, book_id=book_id)

    event = UserPersonalRecoEVENT(
        user_id=user.sub,
        type=UserEventENUM.CART_ADD,
        book_id=book_id,
    )

    await publish_user_personal_books_reco_rmq_safe(
        routing_key="events.cart_add",
        event=event,
        correlation_id=str(user.sub),
    )

    return {"detail": "book succesfully added to cart"}

@cart_router.patch(
    "/{book_id}/quantity",
    summary="Изменить Количество В Корзине",
    status_code=status.HTTP_200_OK,
)
async def set_cart_item_quantity_router(
    book_id: int,
    session: SessionDependency,
    quantity: int = Query(ge=0, le=100),
    user: UserAuthorizedREQT = Depends(auth_client),
):
    """quantity=0 удаляет позицию. Количество проверяется по остатку на складе."""
    set_quantity = SetCartItemQuantity(
        transaction=SQLAlchemyTransaction(session),
        book_repository=BookSQLAlchemyREPO(session),
        cart_repository=CartSQLAlchemyRepository(session),
        cart_item_repository=CartItemSQLAlchemyRepository(session),
    )
    new_quantity = await set_quantity.set(
        user_id=user.sub,
        book_id=book_id,
        quantity=quantity,
    )

    return {"quantity": new_quantity}
