class RatingFilter:
    title = "Rating"
    parameter_name = "rating"

    def lookups(self, request, model, run_query) -> list[tuple[str, str]]:
        return [
            ("5", "⭐⭐⭐⭐⭐"),
            ("4", "⭐⭐⭐⭐"),
            ("3", "⭐⭐⭐"),
            ("2", "⭐⭐"),
            ("1", "⭐"),
        ]

    async def get_filtered_query(self, query, value, model):
        if value in ["1", "2", "3", "4", "5"]:
            return query.filter(model.rating == int(value))
        return query

from sqlalchemy import select
from app.core.db.postgres import db_helper
class BookCategoryFilter:
    title = "Category"
    parameter_name = "category_filter"

    async def lookups(self, request, model, run_query) -> list[tuple[str, str]]:
        from app.product.db.postgres.models.category import BookCategoryModel

        async with db_helper.session_factory() as session:
            result = await session.execute(
                select(BookCategoryModel.id, BookCategoryModel.title)
                .order_by(BookCategoryModel.title)
            )
            rows = result.all()

        return [(str(row.id), row.title) for row in rows]

    async def get_filtered_query(self, query, value, model):
        try:
            category_id = int(value)
        except (ValueError, TypeError):
            return query
        return query.filter(model.category_id == category_id)