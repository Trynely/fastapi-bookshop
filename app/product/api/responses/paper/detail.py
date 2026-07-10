from pydantic import BaseModel

class PaperTypeDetailRESP(BaseModel):
    id: int
    type_name: str

    model_config = {
        "from_attributes": True
    }