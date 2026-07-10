from typing import Optional
from pydantic import BaseModel

class CategoryDetailRESP(BaseModel):
    id: int
    slug: str
    title: str
    img: Optional[str]

    model_config = {
        "from_attributes": True
    }