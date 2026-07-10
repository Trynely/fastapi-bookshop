from datetime import datetime
from sqladmin import ModelView
from app.admin.column_type_formatters import datetime_format
from app.product.db.postgres.models.book import BookPopularityStatsModel


class BookPopularityStatsAdmin(ModelView, model=BookPopularityStatsModel):
    name = "Popularity Stat"
    name_plural = "Popularity Stats"
    icon = "fa-solid fa-fire"
    identity = "book_popularity_stat"

    # статистика — только чтение
    can_create = False
    can_edit = False

    admin_ignored_fields = []

    column_labels = {
        BookPopularityStatsModel.book_id: "book ID",
        BookPopularityStatsModel.stat_date: "date",
        BookPopularityStatsModel.wishlist_adds: "wishlist adds",
        BookPopularityStatsModel.popularity_score: "score",
        BookPopularityStatsModel.created_at: "created at",
        BookPopularityStatsModel.updated_at: "updated at",
    }
    column_type_formatters = {
        datetime: datetime_format
    }

    # list
    column_list = [
        BookPopularityStatsModel.book_id,
        BookPopularityStatsModel.stat_date,
        BookPopularityStatsModel.sales,
        BookPopularityStatsModel.wishlist_adds,
        BookPopularityStatsModel.reviews,
        BookPopularityStatsModel.popularity_score,
        BookPopularityStatsModel.created_at,
        BookPopularityStatsModel.updated_at,
    ]
    column_searchable_list = [
        BookPopularityStatsModel.book_id,
    ]
    column_sortable_list = [
        BookPopularityStatsModel.stat_date,
        BookPopularityStatsModel.sales,
        BookPopularityStatsModel.popularity_score,
    ]

    page_size = 25
    page_size_options = [25, 50, 100, 200]
