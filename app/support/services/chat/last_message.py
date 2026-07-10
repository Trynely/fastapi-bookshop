from datetime import datetime, timezone
from app.support.models import ChatModel

def touch_chat_last_message(chat: ChatModel):
    chat.last_message_at = datetime.now(timezone.utc)