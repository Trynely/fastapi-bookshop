from app.shared.exception import AppException

class BookPaperTypeNotFoundERR(AppException):
    msg = "book paper type not found"
    code = 404