from app.shared.exception import AppException

class BookCategoryNotFoundERR(AppException):
    msg = "book category not found"
    code = 404