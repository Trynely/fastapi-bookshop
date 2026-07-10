from app.shared.exception import AppException

class JwtInvalidERR(AppException):
    msg = "token is invalid"
    code = 403


class JwtTypeInvalidERR(AppException):
    msg = "token type is invalid"
    code = 401


class JwtInvalidFormatERR(AppException):
    msg = "token is not JWT format"
    code = 401