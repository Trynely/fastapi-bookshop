from typing import Optional

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.agents.serializers import cart_to_dict, to_tool_json
from app.order.db.sqlalchemy.repositories.cart import CartSQLAlchemyRepository
from app.order.usecase.cart.add_item import AddBookToCart
from app.product.exceptions import BookNotFoundERR, BookUnavailableERR


class AddToCartArgs(BaseModel):
    book_id: int = Field(
        description="Id of the book to add (take it from search tool results)",
    )


class GetCartArgs(BaseModel):
    pass


def build_cart_tools(
    add_to_cart_uc: AddBookToCart,
    user_id: int,
    cart_repo: Optional[CartSQLAlchemyRepository] = None,
) -> list[BaseTool]:
    @tool(args_schema=GetCartArgs)
    async def get_cart() -> str:
        """Show the current user's shopping cart: items, quantities, prices, total."""
        cart = await cart_repo.get_by_user_id(user_id=user_id)
        return to_tool_json({"cart": cart_to_dict(cart)})
    
    @tool(args_schema=AddToCartArgs)
    async def add_book_to_cart(book_id: int) -> str:
        """Add a book to the current user's cart by book id."""
        try:
            await add_to_cart_uc.add(
                user_id=user_id,
                book_id=book_id,
            )
        except BookNotFoundERR:
            return to_tool_json({
                "success": False,
                "message": f"book {book_id} not found",
            })
        except BookUnavailableERR:
            return to_tool_json({
                "success": False,
                "message": f"book {book_id} is currently unavailable",
            })

        return to_tool_json({
            "success": True,
            "message": f"book {book_id} added to cart",
        })

    return [get_cart, add_book_to_cart]
