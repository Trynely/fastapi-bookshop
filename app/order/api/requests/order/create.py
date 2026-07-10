from pydantic import BaseModel, Field, field_validator

class OrderItemREQT(BaseModel):
    book_id: int
    quantity: int = Field(gt=0)


class CreateOrderREQT(BaseModel):
    items: list[OrderItemREQT]

    @field_validator("items")
    @classmethod
    def validate_items_length(cls, v: list[OrderItemREQT]) -> list[OrderItemREQT]:
        if not 1 <= len(v) <= 10:
            raise ValueError("items count must be between 1 and 10")
        return v
