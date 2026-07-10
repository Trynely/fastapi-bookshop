from app.shared.exception import AppException

class BookReviewAlreadyExistsERR(AppException):
    msg = "book review already exists"
    code = 409