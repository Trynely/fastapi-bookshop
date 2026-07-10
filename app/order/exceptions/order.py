from app.shared.exception import AppException

class CartEmptyERR(AppException):
    msg = "cart is empty"
    code = 400


class BooksBusyERR(AppException):
    msg = "these books are being purchased right now, please try again"
    code = 409


class OrderItemsLimitExceededERR(AppException):
    msg = "items count must be between 1 and 10"
    code = 400


class OrderQuantityInvalidERR(AppException):
    msg = "quantity must be positive"
    code = 400


class OrderBookNotAvailableERR(AppException):
    msg = "book is not available"
    code = 409

    def __init__(self, book_id: int | None = None):
        if book_id is not None:
            super().__init__(msg=f"book {book_id} is not available")
        else:
            super().__init__()


class StripeCheckoutERR(AppException):
    msg = "failed to create stripe checkout session"
    code = 502
