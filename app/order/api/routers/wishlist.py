from fastapi import (
    APIRouter,
    Depends,
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
from app.order.usecase.query_handlers.cart.filter import CartFilterQH
from app.order.usecase.query_handlers.wishlist.filter import WishlistFilterQH
from app.order.usecase.wishlist.add_item import AddBookToWishlist
from app.order.usecase.wishlist.remove_item import RemoveBookFromWishlist
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.client.api.dependencies import auth_user
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO

wishlist_router = APIRouter(prefix="/wishlist", tags=["❤️ Избранное"])

@wishlist_router.get(
    "/by/user",
    summary="Список Избранных Книг Пользователя",
    status_code=status.HTTP_200_OK,
)
async def wishlist_user_booklist_router(
    session: SessionDependency,
    user: UserAuthorizedREQT = Depends(auth_user),
):
    repo = BookSQLAlchemyREPO(session)
    query = WishlistFilterQH(book_repository=repo)
    return await query.get_wishlist_items_by_user(user_id=user.sub)


@wishlist_router.delete(
    "/{book_id}",
    summary="Удалить Книгу Из Избранных",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_item_from_wishlist_router(
    book_id: int,
    session: SessionDependency,
    user: UserAuthorizedREQT = Depends(auth_user),
):
    wishlist_book = RemoveBookFromWishlist(
        transaction=SQLAlchemyTransaction(session),
        book_repository=BookSQLAlchemyREPO(session),
        user_repository=UserSQLAlchemyREPO(session),
    )
    await wishlist_book.remove(user_id=user.sub, book_id=book_id)

    event = UserPersonalRecoEVENT(
        user_id=user.sub,
        type=UserEventENUM.WISHLIST_DEL,
        book_id=book_id,
    )

    await publish_user_personal_books_reco_rmq_safe(
        routing_key="events.wishlist_remove",
        event=event,
        correlation_id=str(user.sub),
    )

    return {"detail": "book succesfully removed from wishlist"}


@wishlist_router.post(
    "",
    summary="Добавить В Избранное",
    status_code=status.HTTP_201_CREATED,
)
async def add_item_to_wishlist_router(
    session: SessionDependency,
    book_id: int,
    user: UserAuthorizedREQT = Depends(auth_user),
):
    wishlist_book = AddBookToWishlist(
        transaction=SQLAlchemyTransaction(session),
        book_repository=BookSQLAlchemyREPO(session),
        user_repository=UserSQLAlchemyREPO(session),
    )
    await wishlist_book.add(user_id=user.sub, book_id=book_id)

    event = UserPersonalRecoEVENT(
        user_id=user.sub,
        type=UserEventENUM.WISHLIST_ADD,
        book_id=book_id,
    )

    await publish_user_personal_books_reco_rmq_safe(
        routing_key="events.wishlist_add",
        event=event,
        correlation_id=str(user.sub),
    )

    return {"detail": "book succesfully added to wishlist"}