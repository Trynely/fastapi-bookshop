from app.shared.exception import AppException


class InvalidRecoCursorEXC(AppException):
    msg = "invalid recommendations cursor"
    code = 400
