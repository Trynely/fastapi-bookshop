from datetime import datetime, timezone

from app.support.models import ChatModel

def close_chat(chat: ChatModel):
    chat.is_closed = True
    chat.closed_at = datetime.now(timezone.utc)