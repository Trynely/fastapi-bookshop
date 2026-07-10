from app.order.db.models.order import (
    OrderStatusENUM,
    PaymentMethodENUM,
    PaymentStatusENUM,
)


class OrderStatusFilter:
    title = "Order Status"
    parameter_name = "status"

    def lookups(self, request, model, run_query) -> list[tuple[str, str]]:
        return [
            (status.value, status.value.capitalize())
            for status in OrderStatusENUM
        ]

    async def get_filtered_query(self, stmt, value, model):
        if value:
            stmt = stmt.where(model.status == value)

        return stmt


class PaymentStatusFilter:
    title = "Payment Status"
    parameter_name = "status"

    def lookups(self, request, model, run_query) -> list[tuple[str, str]]:
        return [
            (status.value, status.value.capitalize())
            for status in PaymentStatusENUM
        ]

    async def get_filtered_query(self, stmt, value, model):
        if value:
            stmt = stmt.where(model.status == value)

        return stmt


class PaymentMethodFilter:
    title = "Payment Method"
    parameter_name = "method"

    def lookups(self, request, model, run_query) -> list[tuple[str, str]]:
        return [
            (method.value, method.value.capitalize())
            for method in PaymentMethodENUM
        ]

    async def get_filtered_query(self, stmt, value, model):
        if value:
            stmt = stmt.where(model.method == value)

        return stmt
