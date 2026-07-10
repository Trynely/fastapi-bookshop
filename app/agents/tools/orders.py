from typing import Optional

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.agents.config.base import AGENT_ORDERS_LIST_LIMIT
from app.agents.serializers import order_to_dict, to_tool_json
from app.order.db.models.order import OrderStatusENUM
from app.order.db.sqlalchemy.repositories.order import OrderSQLAlchemyRepository


class GetOrderArgs(BaseModel):
    order_id: Optional[int] = Field(
        default=None,
        description=(
            "Order number, e.g. 25 for 'заказ №25'. "
            "Omit it to get the user's most recent order."
        ),
    )


class ListOrdersArgs(BaseModel):
    status: Optional[OrderStatusENUM] = Field(
        default=None,
        description=(
            "Filter by status: pending | paid | shipped | delivered | canceled. "
            "Omit to get orders with any status."
        ),
    )
    limit: int = Field(
        default=AGENT_ORDERS_LIST_LIMIT,
        description="Maximum number of orders to return",
        ge=1,
        le=50,
    )


def build_order_tools(
    order_repo: OrderSQLAlchemyRepository,
    user_id: int,
) -> list[BaseTool]:
    @tool(args_schema=GetOrderArgs)
    async def get_order(order_id: Optional[int] = None) -> str:
        """Get one order of the current user: by number, or the latest one if no number is given."""
        if order_id is not None:
            order = await order_repo.get_by_id_for_user(
                order_id=order_id,
                user_id=user_id,
            )
        else:
            order = await order_repo.get_last_for_user(user_id=user_id)

        if order is None:
            return to_tool_json({
                "order": None,
                "message": "order not found for this user",
            })

        return to_tool_json({"order": order_to_dict(order)})

    @tool(args_schema=ListOrdersArgs)
    async def list_orders(
        status: Optional[OrderStatusENUM] = None,
        limit: int = AGENT_ORDERS_LIST_LIMIT,
    ) -> str:
        """List the current user's orders, newest first, optionally filtered by status."""
        orders = await order_repo.get_list_for_user(
            user_id=user_id,
            status=status,
            limit=limit,
        )

        if not orders:
            return to_tool_json({
                "orders": [],
                "message": "no orders found",
            })

        return to_tool_json({
            "orders": [order_to_dict(order) for order in orders],
        })

    return [get_order, list_orders]
