def schat_manager_lock_key(chat_id: int) -> str:
    return f"schat:manager-lock:{chat_id}"

SCHAT_MANAGER_LOCK_TTL = 3600
