from app.shared.exception import AppException

class ChatNotFound(AppException):
    msg = "chat not found or closed"
    code = 404