import json

import stripe
from fastapi import (
    APIRouter,
    Depends,
    Request,
    status,
)

from app.client.api.dependencies import auth_client
from app.client.api.requests.user.auth import UserAuthorizedREQT
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO
from app.core.config.base import get_settings
from app.core.db.postgres import SessionDependency
from app.order.api.requests.order.create import CreateOrderREQT
from app.order.db.sqlalchemy.repositories.cart import CartSQLAlchemyRepository
from app.order.db.sqlalchemy.repositories.order import (
    OrderSQLAlchemyRepository,
    PaymentSQLAlchemyRepository,
)
from app.order.usecase.order.buy_cart import BuyCart
from app.order.usecase.order.cancel import CancelOrder
from app.order.usecase.order.confirm_payment import ConfirmOrderPayment
from app.order.usecase.order.purchase import BuyBooks
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction

settings = get_settings()

order_router = APIRouter(prefix="/orders", tags=["⚜ Заказы"])

@order_router.post(
    "",
    summary="Купить Книги",
    status_code=status.HTTP_201_CREATED,
)
async def purchase_books_router(
    data: CreateOrderREQT,
    session: SessionDependency,
    user: UserAuthorizedREQT = Depends(auth_client),
):
    purchase = BuyBooks(
        transaction=SQLAlchemyTransaction(session),
        book_repository=BookSQLAlchemyREPO(session),
        user_repository=UserSQLAlchemyREPO(session),
        order_repository=OrderSQLAlchemyRepository(session),
        payment_repository=PaymentSQLAlchemyRepository(session),
    )
    result = await purchase.buy(user_id=user.sub, order_data=data)

    return {"checkout_url": result.stripe_checkout_url}


@order_router.post(
    "/from-cart",
    summary="Купить Книги Из Корзины",
    status_code=status.HTTP_201_CREATED,
)
async def purchase_cart_router(
    session: SessionDependency,
    user: UserAuthorizedREQT = Depends(auth_client),
):
    buy_books = BuyBooks(
        transaction=SQLAlchemyTransaction(session),
        book_repository=BookSQLAlchemyREPO(session),
        user_repository=UserSQLAlchemyREPO(session),
        order_repository=OrderSQLAlchemyRepository(session),
        payment_repository=PaymentSQLAlchemyRepository(session),
    )
    purchase = BuyCart(
        cart_repository=CartSQLAlchemyRepository(session),
        buy_books=buy_books,
    )
    result = await purchase.buy(user_id=user.sub)

    return {"checkout_url": result.stripe_checkout_url}


@order_router.post(
    "/webhook",
    summary="Stripe Webhook",
    include_in_schema=False,
)
async def stripe_webhook_router(
    request: Request,
    session: SessionDependency,
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.stripe.webhook_secret,
        )
    except (ValueError, json.JSONDecodeError):
        return {"status": "invalid payload"}
    except stripe.error.SignatureVerificationError:
        return {"status": "invalid signature"}

    if event["type"] == "checkout.session.completed":
        session_data = event["data"]["object"]

        confirm = ConfirmOrderPayment(
            transaction=SQLAlchemyTransaction(session),
            order_repository=OrderSQLAlchemyRepository(session),
            payment_repository=PaymentSQLAlchemyRepository(session),
            cart_repository=CartSQLAlchemyRepository(session),
        )
        await confirm.confirm(
            order_id=int(session_data["metadata"]["order_id"]),
            payment_id=int(session_data["metadata"]["payment_id"]),
            payment_intent_id=session_data.get("payment_intent"),
        )

    elif event["type"] == "checkout.session.expired":
        # покупатель не оплатил за отведённое время —
        # отменяем заказ и возвращаем книги на склад
        session_data = event["data"]["object"]

        cancel = CancelOrder(
            transaction=SQLAlchemyTransaction(session),
            order_repository=OrderSQLAlchemyRepository(session),
            payment_repository=PaymentSQLAlchemyRepository(session),
            book_repository=BookSQLAlchemyREPO(session),
        )
        await cancel.cancel(
            order_id=int(session_data["metadata"]["order_id"]),
        )

    return {"status": "ok"}


@order_router.get(
    "/success",
    summary="Страница Успешной Оплаты",
)
async def order_success_router(order_id: int):
    return {"message": f"Заказ {order_id} успешно оплачен!"}


@order_router.get(
    "/cancel",
    summary="Страница Отмены Оплаты",
)
async def order_cancel_router(order_id: int):
    return {"message": f"Оплата заказа {order_id} отменена"}
