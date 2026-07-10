from app.shared.exception import AppException

class TooManySChatMessages(AppException):
    msg = "sending messages to the support chat too often"
    code = 429