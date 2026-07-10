from app.shared.exception import AppException

class ManagerNotFound(AppException):
    msg = "manager not found"
    code = 404


class ManagerAlreadyAssigned(AppException):
    msg = "manager is already assigned to the chat"
    code = 409


class ManagerNotAssigned(AppException):
    msg = "manager is not assigned to this chat"
    code = 403


class ManagerAlreadyConnected(AppException):
    msg = "manager is already connected to this chat"
    code = 409