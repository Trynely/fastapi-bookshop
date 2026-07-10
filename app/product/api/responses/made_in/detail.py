from pydantic import BaseModel

class MadeInDetailRESP(BaseModel):
    id: int
    slug: str
    country: str

    model_config = {
        "from_attributes": True
    }