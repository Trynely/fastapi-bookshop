from dataclasses import dataclass
from datetime import datetime, timezone

@dataclass(frozen=True, slots=True)
class PaperTypeDTOTestConf:
    id: int = 1
    type_name: str = "Hardcover"

    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

paper_dto_test_conf = PaperTypeDTOTestConf()