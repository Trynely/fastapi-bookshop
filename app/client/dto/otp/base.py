from __future__ import annotations
from dataclasses import dataclass
import uuid
    
@dataclass(frozen=True)
class OtpDTO:
    owner: str
    code: str
    ttl: int
    session_id: uuid = None