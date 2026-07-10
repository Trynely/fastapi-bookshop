from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

# Повторяем Enum для типизации в схемах
from enum import Enum

class ChatMessageSender(str, Enum):
    USER = "user"
    BOT = "bot"
    MANAGER = "manager"

class EscalationReason(str, Enum):
    OPERATOR_REQUEST = "operator_request"
    COMPLEX_CASE = "complex_case"
    PROFANITY = "profanity"

# --- Схемы для Сообщений ---

class ChatMessageBase(BaseModel):
    content: str
    sender: ChatMessageSender

class ChatMessageCreate(ChatMessageBase):
    pass

class ChatMessageRead(ChatMessageBase):
    id: int
    chat_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Схемы для Чата ---

class ChatBase(BaseModel):
    user_id: int
    manager_id: Optional[int] = None
    is_closed: bool = False
    escalation_reason: Optional[EscalationReason] = None

class ChatCreate(BaseModel):
    user_id: int

class ChatUpdate(BaseModel):
    manager_id: Optional[int] = None
    is_closed: Optional[bool] = None
    escalation_reason: Optional[EscalationReason] = None
    closed_at: Optional[datetime] = None

class ChatRead(ChatBase):
    id: int
    closed_at: Optional[datetime] = None
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime
    
    # Если нужно сразу отдавать список сообщений
    # messages: List[ChatMessageRead] = []

    model_config = ConfigDict(from_attributes=True)

# --- Схема с вложенными данными (Full) ---

class ChatFull(ChatRead):
    messages: List[ChatMessageRead]
    # Можно добавить краткую инфу о пользователе, если есть UserRead схема
    # user: Optional[UserRead] = None 