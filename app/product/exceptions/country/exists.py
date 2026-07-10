from app.shared.exception import AppException

class BookMadeInNotFoundERR(AppException):
    msg = "book made in country not found"
    code = 404