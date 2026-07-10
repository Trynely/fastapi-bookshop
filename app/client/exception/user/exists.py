from app.shared.exception import AppException

class UserNotFoundERR(AppException):
    msg = "user not found"
    code = 404


class UserAlreadyExistsERR(AppException):
    msg = 'user with this email already exists'
    code = 409