from dataclasses import dataclass, field
import uuid

@dataclass(frozen=True)
class JWTRefreshTokenDTO:
    sub: str
    jti: str = field(default_factory=lambda: str(uuid.uuid4()))