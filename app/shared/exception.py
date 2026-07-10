class AppException(Exception):
    msg: str = "an unknown error occurred"
    code: int = 500

    def __init__(
        self,
        msg: str | None = None,
        code: int | None = None
    ):
        if msg is not None:
            self.msg = msg
            
        if code is not None:
            self.code = code

    def __str__(self):
        return f"[{self.code}] {self.msg}"