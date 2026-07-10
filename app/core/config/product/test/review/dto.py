from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

@dataclass(frozen=True, slots=True)
class ReviewDTOTestConf:
    id: int = 1
    rating: Optional[int] = 5
    comment: Optional[str] = "Excellent book on software architecture"

    book_id: int = 1
    user_id: Optional[int] = 1

    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

review_dto_test_conf = ReviewDTOTestConf()