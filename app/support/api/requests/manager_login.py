from pydantic import BaseModel, field_validator


class ManagerLoginREQT(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, email: str) -> str:
        return email.strip().lower()
