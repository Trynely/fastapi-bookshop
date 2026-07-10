from app.shared.exception import AppException

class BookNotFoundERR(AppException):
    msg = "book not found"
    code = 404


class BookUnavailableERR(AppException):
    msg = "book unavailable"
    code = 400