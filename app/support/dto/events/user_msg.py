from pydantic import BaseModel

class ChatUserMsgEVT(BaseModel):
    model_config = {"frozen": True}

    chat_id: int
    message: str
