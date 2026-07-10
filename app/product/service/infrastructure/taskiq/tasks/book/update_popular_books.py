import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import or_, select, func
from sqlalchemy.dialects.postgresql import insert
from app.client.db.postgres.models import UserEventENUM, UserEventModel
from app.order.db.models.order import OrderItemModel
from app.order.db.models.wishlist import WishlistModel
from app.product.db.postgres.models.book import BookModel, BookPopularityStatsModel
from app.product.db.postgres.models.review import ReviewModel
from app.core.db.postgres import db_helper
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker

logger = logging.getLogger(__name__)

POPULARITY_WEIGHT_SALES = Decimal("0.60")
POPULARITY_WEIGHT_WISHLIST = Decimal("0.30")
POPULARITY_WEIGHT_REVIEWS = Decimal("0.05")
POPULARITY_WEIGHT_RATING  = Decimal("0.05")

# Просмотры — слабый, но самый ранний сигнал: пока нет продаж и отзывов,
# только они отличают "Популярное" от случайной выборки. Считаем уникальных
# зрителей (count distinct user_id), а не сырые просмотры — один пользователь
# не накрутит книгу рефрешами. С появлением продаж вес 0.60 их перевесит.
POPULARITY_WEIGHT_VIEWS = Decimal("0.10")

POPULARITY_BATCH_SIZE = 1000


@taskiq_broker.task(schedule=[{"cron": "10 0 * * *"}])  # 00:10 UTC ежедневно
async def update_books_popularity() -> None:
    today_utc = datetime.now(tz=timezone.utc).date()
    yesterday_utc = today_utc - timedelta(days=1)
    yesterday_start = datetime.combine(yesterday_utc, datetime.min.time()).replace(tzinfo=timezone.utc)
    today_start = datetime.combine(today_utc, datetime.min.time()).replace(tzinfo=timezone.utc)

    async with db_helper.session_factory() as session:
        try:
            sales_sq = (
                select(
                    OrderItemModel.book_id,
                    func.count(1).label("sales"),
                )
                .where(
                    OrderItemModel.created_at >= yesterday_start,
                    OrderItemModel.created_at < today_start,
                )
                .group_by(OrderItemModel.book_id)
                .subquery()
            )

            wishlist_sq = (
                select(
                    WishlistModel.book_id,
                    func.count(1).label("wishlist_adds"),
                )
                .where(
                    WishlistModel.created_at >= yesterday_start,
                    WishlistModel.created_at < today_start,
                )
                .group_by(WishlistModel.book_id)
                .subquery()
            )

            reviews_sq = (
                select(
                    ReviewModel.book_id,
                    func.count(1).label("reviews"),
                )
                .where(
                    ReviewModel.created_at >= yesterday_start,
                    ReviewModel.created_at < today_start,
                )
                .group_by(ReviewModel.book_id)
                .subquery()
            )

            views_sq = (
                select(
                    UserEventModel.book_id,
                    func.count(func.distinct(UserEventModel.user_id)).label("views"),
                )
                .where(
                    UserEventModel.event_type == UserEventENUM.VIEW,
                    UserEventModel.book_id.is_not(None),
                    UserEventModel.created_at >= yesterday_start,
                    UserEventModel.created_at < today_start,
                )
                .group_by(UserEventModel.book_id)
                .subquery()
            )

            sales_col = func.coalesce(sales_sq.c.sales, 0)
            wishlist_col = func.coalesce(wishlist_sq.c.wishlist_adds, 0)
            reviews_col = func.coalesce(reviews_sq.c.reviews, 0)
            views_col = func.coalesce(views_sq.c.views, 0)
            # coalesce обязателен: NULL-рейтинг иначе занулял бы весь score
            rating_col = func.coalesce(BookModel.rating, 0)

            stmt = (
                select(
                    BookModel.id.label("book_id"),
                    sales_col.label("sales"),
                    wishlist_col.label("wishlist_adds"),
                    reviews_col.label("reviews"),
                    (
                        sales_col * POPULARITY_WEIGHT_SALES
                        + wishlist_col * POPULARITY_WEIGHT_WISHLIST
                        + reviews_col * POPULARITY_WEIGHT_REVIEWS
                        + rating_col * POPULARITY_WEIGHT_RATING
                        + views_col * POPULARITY_WEIGHT_VIEWS
                    ).label("popularity_score"),
                )
                .outerjoin(sales_sq, sales_sq.c.book_id == BookModel.id)
                .outerjoin(wishlist_sq, wishlist_sq.c.book_id == BookModel.id)
                .outerjoin(reviews_sq, reviews_sq.c.book_id == BookModel.id)
                .outerjoin(views_sq, views_sq.c.book_id == BookModel.id)
                .where(
                    BookModel.is_available.is_(True),
                    or_(
                        sales_sq.c.sales > 0,
                        wishlist_sq.c.wishlist_adds > 0,
                        reviews_sq.c.reviews > 0,
                        views_sq.c.views > 0,
                    ),
                )
            )

            total_upserted = 0
            stream_result = await session.stream(stmt)
            async for partition in stream_result.partitions(POPULARITY_BATCH_SIZE):
                insert_stmt = insert(BookPopularityStatsModel).values(
                    [
                        {
                            "book_id": row.book_id,
                            "sales": row.sales,
                            "wishlist_adds": row.wishlist_adds,
                            "reviews": row.reviews,
                            "popularity_score": row.popularity_score,
                            "stat_date": yesterday_utc,
                        }
                        for row in partition
                    ]
                )
                insert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["book_id", "stat_date"],
                    set_={
                        "sales": insert_stmt.excluded.sales,
                        "wishlist_adds": insert_stmt.excluded.wishlist_adds,
                        "reviews": insert_stmt.excluded.reviews,
                        "popularity_score": insert_stmt.excluded.popularity_score,
                        "updated_at": func.now(),
                    },
                )
                await session.execute(insert_stmt)
                total_upserted += len(partition)

            await session.commit()
            logger.info(
                "update_books_popularity: upserted %d rows for %s",
                total_upserted,
                yesterday_utc,
            )

        except Exception:
            await session.rollback()
            logger.exception(
                "update_books_popularity: failed for %s, transaction rolled back",
                yesterday_utc,
            )
            raise