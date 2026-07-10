from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class WishlistItemsResponse(BaseModel):
    id: int
    slug: str
    title: str
    price: Decimal
    img: str | None

    model_config = ConfigDict(from_attributes=True)