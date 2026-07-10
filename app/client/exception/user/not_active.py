from app.shared.exception import AppException

class UserNotActiveERR(AppException):
    msg = "user unavailable"
    code = 400