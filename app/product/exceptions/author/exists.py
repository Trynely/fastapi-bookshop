from app.shared.exception import AppException

class BookAuthorNotFoundERR(AppException):
    msg = "book author not found"
    code = 404