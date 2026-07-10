import json
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from app.order.db.models.order import OrderModel
from app.product.db.postgres.models.book import BookModel

if TYPE_CHECKING:
    # direct import would create a circular chain:
    # cart model -> client models -> cart model
    from app.order.db.models.cart import CartModel


def _final_price(book: BookModel) -> Decimal:
    if book.discount_percent:
        multiplier = Decimal(100 - book.discount_percent) / Decimal(100)
        return (book.price * multiplier).quantize(Decimal("0.01"))
    return book.price


def book_to_dict(book: BookModel, score: float | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": book.id,
        "title": book.title,
        "author": book.author.name if book.author else None,
        "category": book.category.title if book.category else None,
        "price_eur": str(_final_price(book)),
        "rating": str(book.rating),
        "issue_year": book.issue_year,
        "description": (book.description or "")[:300],
    }

    if score is not None:
        data["relevance_score"] = round(score, 3)

    return data


def order_to_dict(order: OrderModel) -> dict[str, Any]:
    return {
        "order_id": order.id,
        "status": order.status.value,
        "total_amount_eur": str(order.total_amount),
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "payment_status": (
            order.payment.status.value if order.payment else None
        ),
        "items": [
            {
                "book_id": item.book_id,
                "title": item.book.title if item.book else None,
                "quantity": item.quantity,
                "price_eur": str(item.price),
            }
            for item in order.items
        ],
    }


def cart_to_dict(cart: "CartModel | None") -> dict[str, Any]:
    if cart is None or not cart.items:
        return {"items": [], "total_eur": "0.00"}

    items = []
    total = Decimal("0.00")

    for item in cart.items:
        price = _final_price(item.book) if item.book else Decimal("0.00")
        subtotal = price * item.quantity
        total += subtotal

        items.append({
            "book_id": item.book_id,
            "title": item.book.title if item.book else None,
            "author": (
                item.book.author.name
                if item.book and item.book.author else None
            ),
            "quantity": item.quantity,
            "price_eur": str(price),
            "subtotal_eur": str(subtotal),
        })

    return {"items": items, "total_eur": str(total)}


def to_tool_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)
