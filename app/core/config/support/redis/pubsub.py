def schat_channel(chat_id: int) -> str:
    return f"schat:{chat_id}"

def schat_user_kick_channel(user_id: int) -> str:
    return f"schat:kick_user:{user_id}"