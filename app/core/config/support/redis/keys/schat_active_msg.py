def user_active_msg_chat_key(*args, **kwargs):
    user_id = kwargs.get("user_id")
    
    if user_id is None and args:
        if hasattr(args[0], "__dict__") or isinstance(args[0], type):
            user_id = args[1] if len(args) > 1 else None
        else:
            user_id = args[0]
            
    return f"user:schat-active:{user_id}"

USER_ACTIVE_MSG_SCHAT_TLL = 3600