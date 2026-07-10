from pydantic import BaseModel, EmailStr

class UserOauthREQT(BaseModel):
    email: EmailStr
    oauth_id: str
    username: str