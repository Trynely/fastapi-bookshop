def rate_limit_msg_schat_key(user_id: int) -> str:
    return f"rate-limit:schat:{user_id}"

RATE_LIMIT_MSG_SCHAT_TTL = 10