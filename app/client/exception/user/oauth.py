from app.shared.exception import AppException

class OAuthProviderMismatchERR(AppException):
    msg = "account already registered with another authentication provider"
    code = 409


class GoogleAccountSecurityERR(AppException):
    msg = "google account identity mismatch detected"
    code = 403


class GoogleEmailNotVerifiedERR(AppException):
    msg = "google email not verified"
    code = 400


class IsOAuthUserERR(AppException):
    msg = "user uses oauth authorization"
    code = 409