from app.shared.exception import AppException

class JwtExpiredERR(AppException):
    msg = "token has expired"
    code = 401