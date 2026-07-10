from app.shared.exception import AppException

class ReviewRatingInvalidERR(AppException):
    msg = "rating should be from 1 to 5"
    code = 422