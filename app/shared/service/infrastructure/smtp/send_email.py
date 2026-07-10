from app.core.config.base import get_settings
from urllib.parse import urlparse
import smtplib
from email.mime.text import MIMEText
import logging

from app.core.config.shared.smtp.gmail_metadata import (
    GMAIL_LETTER_FROM,
    GMAIL_LETTER_TO,
    GMAIL_SUBJECT,
)

settings = get_settings()
logger = logging.getLogger(__name__)

def send_letter_to_email(
    body: str,
    subject: str,
    send_from: str,
    send_to: str,
) -> None:
    msg = MIMEText(body, _charset="utf-8")
    msg[GMAIL_SUBJECT] = subject
    msg[GMAIL_LETTER_FROM] = send_from
    msg[GMAIL_LETTER_TO] = send_to

    parsed = urlparse(settings.smtp.dsn)
    smtp_host = parsed.hostname
    smtp_port = parsed.port or (465 if parsed.scheme == "smtps" else 587)
    smtp_user = parsed.username
    smtp_pass = parsed.password

    smtp = None
    
    try:
        if parsed.scheme == "smtps":
            smtp = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            smtp = smtplib.SMTP(smtp_host, smtp_port)
            smtp.starttls()

        if smtp_user and smtp_pass:
            smtp.login(smtp_user, smtp_pass)

        smtp.sendmail(msg[GMAIL_LETTER_FROM], [msg[GMAIL_LETTER_TO]], msg.as_string())
        logger.info(f"otp email has been successfully sent to {send_to}")
    except Exception as e:
        logger.error(f"error when sending OTP email to {send_to}: {e}")
        raise
    finally:
        if smtp:
            try:
                smtp.quit()
            except Exception:
                pass