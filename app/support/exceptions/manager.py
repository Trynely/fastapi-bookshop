from app.shared.exception import AppException

class ManagerNotFound(AppException):
    msg = "manager not found"
    code = 404


class ManagerAlreadyAssigned(AppException):
    msg = "manager is already assigned to the chat"
    code = 409