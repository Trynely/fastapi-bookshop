from app.shared.exception import AppException

class ChatNotFound(AppException):
    msg = "chat not found or closed"
    code = 404


class ChatIsClosed(AppException):
    msg = "chat is closed"
    code = 401