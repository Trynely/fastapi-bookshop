from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field

class UserAuthorizedREQT(BaseModel):
    type: Literal["access_token"]
    jti: str
    exp: int
    iat: int
    sub: int = Field(..., description="User ID")
    role: str | None = None


class UserAuthConfirmREQT(BaseModel):
    session_id: UUID
    otp: str