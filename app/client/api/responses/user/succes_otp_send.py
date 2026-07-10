import uuid

def succes_otp_sending_to_email_resp(session_id: uuid):
    return {
        "success": "confirmation code has been successfully sent to your email",
        "session_id": session_id,
    }