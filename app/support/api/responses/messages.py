from typing import Any, Dict, List
from pydantic import BaseModel
from app.support.api.responses.websoket import WSMessageTypeEnum
from app.support.usecase.query_handlers.messages.filter import ChatMessageSchema

class ChatMessagesHistoryRESP(BaseModel):
    type: WSMessageTypeEnum
    data: Dict[str, Any]


class HistoryPayload(BaseModel):
    messages: List[ChatMessageSchema]