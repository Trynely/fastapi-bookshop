from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from app.shared.api.responses.page_pagination import PagePaginationRESP
from app.client.api.responses.user.for_review import UserReviewPreviewRESP

class ReviewPreviewRESP(BaseModel):
    id: int

    rating: Optional[int]
    comment: Optional[str]

    created_at: datetime
    updated_at: datetime

    user: Optional[UserReviewPreviewRESP]

    model_config = {
        "from_attributes": True
    }


class ReviewsPreviewPaginationRESP(PagePaginationRESP):
    reviews: List[ReviewPreviewRESP]