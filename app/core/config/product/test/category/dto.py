from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

@dataclass(frozen=True, slots=True)
class BookCategoryDTOTestConf:
    id: int = 1
    slug: str = "software-architecture"
    title: str = "Software Architecture"
    img: Optional[str] = "categories/software-architecture.jpg"

    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)


book_category_dto_test_conf = BookCategoryDTOTestConf()