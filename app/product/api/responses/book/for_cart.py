from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class BookCartItemResponse(BaseModel):
    id: int
    slug: str
    title: str
    price: Decimal
    img: str | None
    quantity: int  # остаток на складе
    is_available: bool

    model_config = ConfigDict(from_attributes=True)