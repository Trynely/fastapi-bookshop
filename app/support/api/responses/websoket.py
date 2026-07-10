from enum import Enum

class WSMessageKeysEnum(str, Enum):
    TYPE = "type"
    ACTION = "action"

class WSMessageTypeEnum(str, Enum):
    HISTORY = "history"
    MESSAGE = "message"
    SYSTEM = "system"
    ERROR = "error"


class WSMessageActionEnum(str, Enum):
    CLOSE = "close"