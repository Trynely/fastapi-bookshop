from app.shared.exception import AppException

class OtpNotExpiredERR(AppException):
    msg = 'the confirmation code was sent earlier'
    code = 409


class OtpExpiredERR(AppException):
    msg = 'the confirmation code expired'
    code = 400