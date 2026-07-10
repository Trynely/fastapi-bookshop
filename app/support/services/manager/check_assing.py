from app.support.models import ChatModel

def chat_has_no_manager(chat: ChatModel) -> bool:
    return not chat.manager_id