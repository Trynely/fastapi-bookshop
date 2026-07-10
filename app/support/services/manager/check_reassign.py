from app.support.models import ChatModel

def check_same_manager(chat: ChatModel, manager_id: int) -> bool:
    return manager_id == chat.manager_id