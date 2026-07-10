from app.shared.exception import AppException

class UserAlreadyAuthorizedERR(AppException):
    msg = "you are already logged in"
    code = 409