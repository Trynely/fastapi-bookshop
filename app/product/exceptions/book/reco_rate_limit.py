from app.shared.exception import AppException

class TooManyRecoFeedSessionsERR(AppException):
    msg = "too many new recommendation feed sessions, slow down"
    code = 429
