from app.shared.exception import AppException

class JwtRefreshReplayDetectedERR(AppException):
    msg = "refresh token replay detected"
    code = 401