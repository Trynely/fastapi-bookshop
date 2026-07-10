from app.core.config.base import get_settings
from app.core.config.client.otp.email.body import get_email_otp_body_conf
from app.core.config.client.otp.email.subject import OTP_EMAIL_SUBJECT_CONF
from app.shared.service.infrastructure.smtp.send_email import send_letter_to_email
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

@taskiq_broker.task
def send_otp_email(email: str, otp: str) -> None:
    send_letter_to_email(
        body=get_email_otp_body_conf(otp=otp, settings=settings),
        subject=OTP_EMAIL_SUBJECT_CONF,
        send_from=settings.smtp.default_email,
        send_to=email,
    )