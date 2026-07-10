def user_chat_cache_key(*args, **kwargs):
    user_id = kwargs.get("user_id")
    
    if user_id is None and args:
        if hasattr(args[0], "__dict__") or isinstance(args[0], type):
            user_id = args[1] if len(args) > 1 else None
        else:
            user_id = args[0]
            
    return f"cache:user:schat:{user_id}"


def chat_schat_cache_key(*args, **kwargs):
    chat_id = kwargs.get("chat_id")

    if chat_id is None and args:
        if hasattr(args[0], "__dict__") or isinstance(args[0], type):
            chat_id = args[1] if len(args) > 1 else None
        else:
            chat_id = args[0]

    return f"cache:schat:chat:{chat_id}"


USER_SCHAT_CACHE_TTL = 300