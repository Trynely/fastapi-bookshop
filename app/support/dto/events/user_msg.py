from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ChatUserMsgEVT:
    chat_id: int
    message: str