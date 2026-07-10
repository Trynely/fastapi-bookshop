from app.core.config.base import get_settings

def jwt_refresh_session_time_conf() -> int:
    settings = get_settings()
    return settings.jwt.refresh_token_exp_days * 86400

def jwt_refresh_user_sessions_conf(user_id: int) -> str:
    return f"user_refresh_sessions:{user_id}"

def jwt_refresh_user_session_conf(jti: str) -> str:
    return f"refresh:{jti}"