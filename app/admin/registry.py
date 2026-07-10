from app.admin.client.views import ClientAdmin
from app.admin.client.event_views import UserEventAdmin
from app.admin.product.views.author import AuthorAdmin
from app.admin.product.views.book import BookAdmin
from app.admin.product.views.category import CategoryBookAdmin
from app.admin.product.views.country import MadeInBookAdmin
from app.admin.product.views.paper import PaperBookAdmin
from app.admin.product.views.popularity import BookPopularityStatsAdmin
from app.admin.product.views.review import ReviewBookAdmin
from app.admin.order.views.cart import CartAdmin, CartItemAdmin
from app.admin.order.views.order import (
    AddressAdmin,
    OrderAdmin,
    OrderItemAdmin,
    PaymentAdmin,
)
from app.admin.order.views.wishlist import WishlistAdmin
from app.admin.support.views import ChatAdmin, ChatMessageAdmin

ADMIN_VIEWS = [
    # client
    ClientAdmin,
    UserEventAdmin,

    # product
    BookAdmin,
    CategoryBookAdmin,
    AuthorAdmin,
    ReviewBookAdmin,
    PaperBookAdmin,
    MadeInBookAdmin,
    BookPopularityStatsAdmin,

    # order
    CartAdmin,
    CartItemAdmin,
    OrderAdmin,
    OrderItemAdmin,
    PaymentAdmin,
    AddressAdmin,
    WishlistAdmin,

    # support
    ChatAdmin,
    ChatMessageAdmin,
]
