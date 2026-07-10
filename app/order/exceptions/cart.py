from app.shared.exception import AppException

class CartItemNotFoundERR(AppException):
    msg = "cart item not found"
    code = 404


class BookStockExceededERR(AppException):
    code = 409

    def __init__(self, available: int):
        self.available = available
        super().__init__(msg=f"only {available} pcs available")
