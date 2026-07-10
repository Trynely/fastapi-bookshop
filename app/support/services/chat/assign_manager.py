from app.support.models import ChatModel

def assign_manager_to_chat(chat: ChatModel, manager_id: int):
    chat.manager_id = manager_id


def unassign_manager_from_chat(chat: ChatModel):
    chat.manager_id = None