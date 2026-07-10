from app.shared.exception import AppException

class OtpInvalidERR(AppException):
    msg = 'incorrect confirmation code'
    code = 400