from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True, slots=True)
class AuthorDTOTestConf:
    id: int = 1
    slug: str = "robert-c-martin"
    name: str = "Robert C. Martin"

    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

author_dto_test_conf = AuthorDTOTestConf()