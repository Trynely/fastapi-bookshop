from app.client.db.postgres.models import ClientModel
from app.product.db.postgres.models import (
    BookModel,
    BookCategoryModel,
    AuthorModel,
    PaperTypeModel,
    MadeInModel,
    ReviewModel,
)
from app.order.db.models.order import (
    OrderModel,
    OrderItemModel,
    PaymentModel,
    AddressModel,
)
from app.order.db.models.wishlist import WishlistModel
from app.order.db.models.cart import CartModel, CartItemModel
from app.support.models import ChatModel, ChatMessageModel, ReplyTemplateModel