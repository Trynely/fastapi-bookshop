def rate_limit_msg_schat_key(user_id: int) -> str:
    return f"rate-limit:schat:{user_id}"

def schat_violations_key(user_id: int) -> str:
    return f"rate-limit:schat:violations:{user_id}"

def schat_mute_key(user_id: int) -> str:
    return f"schat:mute:{user_id}"

RATE_LIMIT_MSG_SCHAT_TTL = 10
RATE_LIMIT_MSG_SCHAT_MAX = 5

SCHAT_VIOLATIONS_TTL = 300
SCHAT_VIOLATIONS_MAX = 3

SCHAT_MUTE_TTL = 60