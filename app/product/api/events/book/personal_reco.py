from pydantic import BaseModel, Field
from app.client.db.postgres.models import UserEventENUM

class BookPersonalRecoEVENT(BaseModel):
    type: UserEventENUM
    book_id: int | None = None
    metadata: dict = Field(default_factory=dict)


class SearchEventMeta(BaseModel):
    query: str
    results_count: int = 0


class RatingEventMeta(BaseModel):
    rating: int = Field(ge=1, le=5)