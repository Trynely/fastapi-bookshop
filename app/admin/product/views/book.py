import logging
from datetime import datetime
from typing import Any

from sqladmin import ModelView
from sqladmin.filters import BooleanFilter
from starlette.requests import Request
from app.admin.column_type_formatters import datetime_format
from app.admin.product.filters import BookCategoryFilter, RatingFilter
from app.product.db.postgres.models.book import BookModel

logger = logging.getLogger(__name__)


class BookAdmin(ModelView, model=BookModel):
    name = "Book"
    name_plural = "Books"
    icon = "fa-solid fa-book"
    identity = "book"

    admin_ignored_fields = [
        "order_items",
        "wishlisted_by",
        "reviews",
    ]

    column_labels = {
        # Поля из вашего списка
        BookModel.is_available: "available",
        BookModel.total_sales: "sales",
        BookModel.made_in: "made in",
        BookModel.paper_type: "paper",
        BookModel.issue_year: "year of production",
        
        BookModel.discount_percent: "discount",
        BookModel.total_ratings: "total ratings",
        BookModel.sum_ratings: "sum ratings",
        BookModel.category_id: "category ID",
        BookModel.author_id: "author ID",
        BookModel.paper_type_id: "paper type ID",
        BookModel.made_in_id: "made in ID",

        BookModel.created_at: "created at",
        BookModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        BookModel.id,
        BookModel.slug,
        BookModel.title,
        BookModel.price,
        BookModel.quantity,
        BookModel.is_available,
        BookModel.rating,
        BookModel.total_sales,
        BookModel.created_at,
        BookModel.updated_at,
    ]
    column_searchable_list = [
        BookModel.id,
        BookModel.title,
        BookModel.slug,
    ]
    column_sortable_list = [
        BookModel.price,
        BookModel.quantity,
        BookModel.rating,
        BookModel.created_at,
        BookModel.total_sales,
    ]
    column_filters = [
        RatingFilter(),
        BookCategoryFilter(),
        BooleanFilter(BookModel.is_available),
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]

    # detail
    column_details_exclude_list = [
        BookModel.order_items,
        BookModel.wishlisted_by,
        BookModel.reviews,
    ]

    # form
    form_columns = [
        BookModel.slug,
        BookModel.title,
        BookModel.price,
        BookModel.pages,
        BookModel.quantity,
        BookModel.img,
        BookModel.discount_percent,
        BookModel.description,
        BookModel.issue_year,
        BookModel.is_available,

        BookModel.category,
        BookModel.author,
        BookModel.paper_type,
        BookModel.made_in,
    ]

    form_include_pk = True

    # --- событийная синхронизация Qdrant/ES ---

    @staticmethod
    async def _enqueue_book_sync(book_id: int) -> None:
        # импорт внутри метода: задача импортирует broker,
        # а broker — модули задач (на уровне модуля был бы цикл)
        from app.product.service.infrastructure.taskiq.tasks.book.sync_book import (
            sync_book_task,
        )

        try:
            await sync_book_task.kiq(book_id)
        except Exception:
            # админка не должна падать из-за недоступного брокера;
            # cron-переиндексация догонит изменения
            logger.exception("failed to enqueue sync for book %s", book_id)

    async def after_model_change(
        self,
        data: dict,
        model: Any,
        is_created: bool,
        request: Request,
    ) -> None:
        await self._enqueue_book_sync(model.id)

    async def after_model_delete(
        self,
        model: Any,
        request: Request,
    ) -> None:
        await self._enqueue_book_sync(model.id)

    form_ajax_refs = {
        "category": {
            "fields": ("title",),
            "order_by": "id",
            "limit": 5,
        },
        "author": {
            "fields": ("name",),
            "order_by": "id",
            "limit": 5,
        },
        "paper_type": {
            "fields": ("type_name",),
            "order_by": "id",
            "limit": 5,
        },
        "made_in": {
            "fields": ("country",),
            "order_by": "id",
            "limit": 5,
        },
    }