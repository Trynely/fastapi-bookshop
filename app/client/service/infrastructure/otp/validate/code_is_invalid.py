from app.client.dto.otp.base import OtpDTO

def is_invalid_otp_code(otp: OtpDTO, client_code: str) -> bool:
    return not otp.code == str(client_code)