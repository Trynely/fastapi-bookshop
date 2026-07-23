from app.shared.exception import AppException


class CsrfTokenInvalidERR(AppException):
    msg = "csrf token missing or invalid"
    code = 403
