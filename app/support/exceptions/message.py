from app.shared.exception import AppException

class TooManySChatMessages(AppException):
    msg = "sending messages to the support chat too often"
    code = 429


class SChatUserMuted(AppException):
    msg = "you are temporarily muted in the support chat"
    code = 429