from typing import Optional
from pydantic import BaseModel

class ReviewDetailRESP(BaseModel):
    id: int
    rating: Optional[int]
    comment: Optional[str]

    model_config = {
        "from_attributes": True
    }