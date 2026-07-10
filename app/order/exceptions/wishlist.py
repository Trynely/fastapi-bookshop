from app.shared.exception import AppException

class WishlistItemAlreadyExists(AppException):
    msg = "the item already exists in wishlist"
    code = 409


class WishlistItemNotFound(AppException):
    msg = "wishlist item not found"
    code = 404