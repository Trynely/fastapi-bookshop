from app.core.config.base import Settings

def get_email_otp_body_conf(otp: str, settings: Settings) -> str:
    return f"Ваш код: {otp}\nДействителен {settings.otp.ttl // 60} минут"