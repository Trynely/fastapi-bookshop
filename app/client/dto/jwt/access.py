import uuid
from dataclasses import dataclass, field

@dataclass
class JWTAccessTokenDTO:
    sub: str
    role: str
    jti: str = field(default_factory=lambda: str(uuid.uuid4()))