from decimal import Decimal
from pydantic import (
    BaseModel,
    ConfigDict, 
    computed_field,
)
from app.product.api.responses.book.for_cart import BookCartItemResponse

class CartItemDetailResponse(BaseModel):
    id: int
    quantity: int
    book: BookCartItemResponse

    @computed_field
    @property
    def total_price(self) -> Decimal:
        return self.book.price * self.quantity

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    items: list[CartItemDetailResponse]

    @computed_field
    @property
    def total_amount(self) -> Decimal:
        return sum(
            (item.total_price for item in self.items),
            start=Decimal("0.00"),
        )

    @computed_field
    @property
    def total_items(self) -> int:
        return sum(item.quantity for item in self.items)

    model_config = ConfigDict(from_attributes=True)
