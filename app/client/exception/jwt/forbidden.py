from app.shared.exception import AppException


class JwtRoleForbiddenERR(AppException):
    msg = "insufficient role"
    code = 403
