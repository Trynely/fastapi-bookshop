from pydantic import BaseModel

class AuthorDetailRESP(BaseModel):
    id: int
    slug: str
    name: str

    model_config = {
        "from_attributes": True
    }