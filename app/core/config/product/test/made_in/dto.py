from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True, slots=True)
class MadeInDTOTestConf:
    id: int = 1
    slug: str = "usa"
    country: str = "United States"

    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

made_in_dto_test_conf = MadeInDTOTestConf()