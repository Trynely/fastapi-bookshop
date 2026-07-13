import asyncio
import json
import logging
import math
import random
import uuid
from collections import deque
from dataclasses import asdict, dataclass
from enum import StrEnum
from app.shared.service.infrastructure.redis.clients import RedisClient
from qdrant_client.models import ScoredPoint
from sqlalchemy import Row, and_, or_, select
from app.client.db.qdrant.repositories.user.reco_profile import UserRecoProfileQdrantREPO
from app.client.dto.user.reco_profile import UserRecoProfileDTO
from app.client.service.infrastructure.user.reco_profile import UserPersonalBooksRecoProfile
from app.core.db.postgres import DatabaseHelper
from app.product.db.postgres.models.book import BookModel
from app.product.db.postgres.repositories.sqlalchemy.book import (
    BookSQLAlchemyREPO,
    popularity_window_subquery,
)
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.product.exceptions import TooManyRecoFeedSessionsERR
from app.product.dto.book.main_reco import (
    BookBlenderSlotsDTO,
    BookMainRecoCursorDTO,
    BookPersonalizedRecoStatusDTO,
    BookRecommendationsDTO,
)

logger = logging.getLogger(__name__)

FEED_SESSION_TTL = 1800  # 30 минут неактивности
MAX_EXCLUDED_IDS = 400

# Лимит на создание НОВЫХ сессий фида (запрос первой страницы без курсора).
# Каждая новая сессия = новый book_reco:seen:* ключ в Redis; без лимита
# бот, долбящий первую страницу, растит keyspace со скоростью своего RPS.
# Листание с курсором лимит не трогает — оно переиспользует сессию.
NEW_SESSION_RATE_LIMIT = 15
NEW_SESSION_RATE_WINDOW = 60  # секунд

# Кросс-сессионная память показов: книга, уже показанная пользователю,
# не банится, но её вес при сэмплировании умножается на штраф — иначе
# книга с топовым cosine-score возвращается на первую страницу после
# каждого рефреша (seen-session живёт лишь 30 минут).
IMPRESSIONS_TTL = 3 * 86400
MAX_IMPRESSIONS = 300
IMPRESSION_PENALTY = 0.25

# Запас кандидатов сверх limit — на дедупликацию, exclude и диверсификацию.
CANDIDATE_MULTIPLIER = 3
WEIGHTED_SAMPLE_POOL_MULTIPLIER = 4
WIDE_CANDIDATE_MULTIPLIER = 10

# --- холодный фид (нет вектора / нет статистики популярности) ---

COLD_CANDIDATES_CACHE_KEY = "book_reco:cold_candidates:v2"
COLD_CANDIDATES_TTL = 600  # пул общий для всех холодных пользователей
COLD_POOL_BY_SALES = 200
COLD_POOL_BY_NEWEST = 100

# Сглаживание байесовского рейтинга: книга с одной оценкой 5.0
# не должна обгонять книгу с 4.8 и тысячей оценок.
BAYES_RATING_SMOOTHING = 10.0

COLD_DIVERSITY_CATEGORY_CAP = 2
COLD_DIVERSITY_AUTHOR_CAP = 2

# Декоррелируем выборки personalized-cold и popular-fallback на одной странице
POPULAR_FALLBACK_SEED_SALT = 0x9E3779B9


class BookMainRecoSeenSession:
    """
        Показанные book_id за сессию фида.
        Redis-список: RPUSH атомарен, поэтому параллельные запросы
        с одним session_id не теряют обновления друг друга
        (в отличие от read-modify-write поверх строки).
    """

    def __init__(self, redis: RedisClient):
        self._redis = redis

    @staticmethod
    def _reco_seen_session_key(session_id: str) -> str:
        return f"book_reco:seen:{session_id}"

    def new_session_id(self) -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _new_session_rate_key(user_id: int) -> str:
        return f"book_reco:new_sessions_rate:{user_id}"

    async def ensure_new_session_allowed(self, user_id: int) -> None:
        """
            Fixed-window лимитер на создание новых сессий фида.
            INCR + EXPIRE — тот же идиом, что в rate limit саппорт-чата.
        """

        key = self._new_session_rate_key(user_id)

        count = await self._redis.string.incr(key)

        if count == 1:
            await self._redis.key.expire(key, NEW_SESSION_RATE_WINDOW)

        if count > NEW_SESSION_RATE_LIMIT:
            raise TooManyRecoFeedSessionsERR()

    async def get(self, session_id: str) -> list[int]:
        raw = await self._redis.list.lrange(
            self._reco_seen_session_key(session_id), 0, -1
        )
        return [int(value) for value in raw]

    async def add(
        self,
        session_id: str,
        shown_ids: list[int],
    ) -> None:
        if not shown_ids:
            return

        key = self._reco_seen_session_key(session_id)

        await self._redis.list.rpush(key, *map(str, shown_ids))
        await self._redis.list.ltrim(key, -MAX_EXCLUDED_IDS, -1)
        await self._redis.key.expire(key, FEED_SESSION_TTL)

    # --- кросс-сессионные показы (per-user, живут дольше сессии) ---

    @staticmethod
    def _impressions_key(user_id: int) -> str:
        return f"book_reco:impressions:{user_id}"

    async def get_impressions(self, user_id: int) -> set[int]:
        raw = await self._redis.list.lrange(
            self._impressions_key(user_id), 0, -1
        )
        return {int(value) for value in raw}

    async def add_impressions(
        self,
        user_id: int,
        shown_ids: list[int],
    ) -> None:
        if not shown_ids:
            return

        key = self._impressions_key(user_id)

        await self._redis.list.rpush(key, *map(str, shown_ids))
        await self._redis.list.ltrim(key, -MAX_IMPRESSIONS, -1)
        await self._redis.key.expire(key, IMPRESSIONS_TTL)


def _weighted_sample(
    items: list,
    weights: list[float],
    limit: int,
    seed: int,
    key_fn,
) -> list:
    """
        Случайная выборка без повторений с весами.
        key_fn(item) -> уникальный id для дедупликации.

        Топовые элементы попадают чаще (вес пропорционален score),
        но не гарантированно каждый раз — баланс качества и разнообразия.
    """
    
    if not items:
        return []

    total = sum(weights)
    
    if total <= 0:
        norm_weights = [1.0 / len(weights)] * len(weights)
    else:
        norm_weights = [w / total for w in weights]

    rng = random.Random(seed)
    k = min(limit * WEIGHTED_SAMPLE_POOL_MULTIPLIER, len(items))
    candidates = rng.choices(items, weights=norm_weights, k=k)

    seen: set = set()
    result = []
    
    for item in candidates:
        uid = key_fn(item)
        if uid not in seen:
            seen.add(uid)
            result.append(item)
        if len(result) >= limit:
            break

    if len(result) < limit:
        logger.info(
            "_weighted_sample: pool exhausted, falling back to score order "
            "(have=%d, need=%d, pool_size=%d)",
            len(result),
            limit,
            len(items),
        )

        for item in items:
            uid = key_fn(item)
            if uid not in seen:
                seen.add(uid)
                result.append(item)
            if len(result) >= limit:
                break

    return result


@dataclass(slots=True)
class ColdCandidateDTO:
    id: int
    category_id: int | None
    author_id: int | None
    quality: float    # байесовский рейтинг, нормирован 0..1
    sales: float      # log1p(total_sales), нормирован 0..1
    freshness: float  # позиция по id среди кандидатов, 0..1


# Пол веса. Когда рейтингов и продаж в каталоге ещё нет (quality=sales=0
# у всех), без пола вес схлопывается в чистую новизну — и фид заливает
# последней добавленной категорией. С полом 0.1 максимальный перекос
# новизны ограничен двукратным (0.2 против 0.1), сэмпл почти равномерный.
COLD_WEIGHT_FLOOR = 0.1


def _cold_quality_weight(candidate: ColdCandidateDTO) -> float:
    """Вес для personalized cold start: качество прежде всего."""
    return (
        COLD_WEIGHT_FLOOR
        + 0.6 * candidate.quality
        + 0.2 * candidate.sales
        + 0.1 * candidate.freshness
    )


def _cold_sales_weight(candidate: ColdCandidateDTO) -> float:
    """Вес для popular-фолбэка: продажи прежде всего."""
    return (
        COLD_WEIGHT_FLOOR
        + 0.25 * candidate.quality
        + 0.55 * candidate.sales
        + 0.1 * candidate.freshness
    )


def _diversified_pick(
    candidates: list[ColdCandidateDTO],
    weights: list[float],
    limit: int,
    seed: int,
    category_cap: int = COLD_DIVERSITY_CATEGORY_CAP,
    author_cap: int = COLD_DIVERSITY_AUTHOR_CAP,
) -> list[int]:
    """
        Взвешенный сэмпл + капы на категорию/автора,
        чтобы холодный топ не оказался 8 книгами одной категории.
    """

    sampled = _weighted_sample(
        items=candidates,
        weights=weights,
        limit=limit * CANDIDATE_MULTIPLIER,
        seed=seed,
        key_fn=lambda c: c.id,
    )

    category_counts: dict[int, int] = {}
    author_counts: dict[int, int] = {}
    result: list[int] = []
    seen: set[int] = set()

    def try_pick(candidate: ColdCandidateDTO) -> None:
        if candidate.id in seen:
            return
        if (
            candidate.category_id
            and category_counts.get(candidate.category_id, 0) >= category_cap
        ):
            return
        if (
            candidate.author_id
            and author_counts.get(candidate.author_id, 0) >= author_cap
        ):
            return

        result.append(candidate.id)
        seen.add(candidate.id)

        if candidate.category_id:
            category_counts[candidate.category_id] = (
                category_counts.get(candidate.category_id, 0) + 1
            )
        if candidate.author_id:
            author_counts[candidate.author_id] = (
                author_counts.get(candidate.author_id, 0) + 1
            )

    # 1) сэмпл с капами
    for candidate in sampled:
        try_pick(candidate)
        if len(result) >= limit:
            return result

    # 2) добираем из полного пула, всё ещё соблюдая капы
    for candidate in candidates:
        try_pick(candidate)
        if len(result) >= limit:
            return result

    # 3) капы невыполнимы на этом пуле — заполняем страницу чем есть
    for candidate in candidates:
        if candidate.id not in seen:
            result.append(candidate.id)
            seen.add(candidate.id)
        if len(result) >= limit:
            break

    return result


class BookColdCandidatesProvider:
    """
        Глобальный пул кандидатов для холодного фида:
        топ продаж + свежие книги, скоринг = байесовский рейтинг,
        log-продажи и новизна. Пул одинаков для всех холодных
        пользователей, поэтому кэшируется в Redis.
    """

    def __init__(
        self,
        db_helper: DatabaseHelper,
        redis: RedisClient,
    ):
        self._db_helper = db_helper
        self._redis = redis

    async def get(self) -> list[ColdCandidateDTO]:
        cached = await self._redis.string.get(COLD_CANDIDATES_CACHE_KEY)

        if cached:
            return [ColdCandidateDTO(**item) for item in json.loads(cached)]

        rows = await self._fetch()
        candidates = self._score(rows)

        await self._redis.string.add(
            COLD_CANDIDATES_CACHE_KEY,
            [asdict(c) for c in candidates],
            ex=COLD_CANDIDATES_TTL,
        )

        return candidates

    async def _fetch(self) -> list[Row]:
        base = select(
            BookModel.id,
            BookModel.category_id,
            BookModel.author_id,
            BookModel.rating,
            BookModel.sum_ratings,
            BookModel.total_sales,
        ).where(BookModel.is_available.is_(True))

        # Вторичный ключ — random_key, НЕ id: когда продаж ещё нет
        # (у всех 0/NULL), сортировка по id превращала "топ продаж"
        # в "200 последних добавленных" — и весь пул состоял из
        # свежезалитых категорий. random_key даёт равномерный срез каталога.
        by_sales = base.order_by(
            BookModel.total_sales.desc().nulls_last(),
            BookModel.random_key.asc(),
        ).limit(COLD_POOL_BY_SALES)

        # Свежие книги отдельным запросом — в топ продаж
        # "за всё время" новинки не попадают месяцами
        by_newest = base.order_by(BookModel.id.desc()).limit(COLD_POOL_BY_NEWEST)

        async with self._db_helper.session_factory() as session:
            sales_rows = (await session.execute(by_sales)).all()
            newest_rows = (await session.execute(by_newest)).all()

        merged: dict[int, Row] = {}
        for row in [*sales_rows, *newest_rows]:
            merged.setdefault(row.id, row)

        return list(merged.values())

    @staticmethod
    def _score(rows: list[Row]) -> list[ColdCandidateDTO]:
        if not rows:
            return []

        rated = [
            float(row.rating)
            for row in rows
            if row.rating is not None and (row.sum_ratings or 0) > 0
        ]
        global_mean = sum(rated) / len(rated) if rated else 0.0

        def bayes(row: Row) -> float:
            votes = float(row.sum_ratings or 0)
            rating = float(row.rating or 0.0)
            return (
                (BAYES_RATING_SMOOTHING * global_mean + rating * votes)
                / (BAYES_RATING_SMOOTHING + votes)
            )

        raw_quality = [bayes(row) for row in rows]
        raw_sales = [math.log1p(float(row.total_sales or 0)) for row in rows]

        max_quality = max(raw_quality) or 1.0
        max_sales = max(raw_sales) or 1.0

        ids_sorted = sorted(row.id for row in rows)
        freshness_rank = {bid: idx for idx, bid in enumerate(ids_sorted)}
        rank_denom = max(len(rows) - 1, 1)

        return [
            ColdCandidateDTO(
                id=row.id,
                category_id=row.category_id,
                author_id=row.author_id,
                quality=quality / max_quality,
                sales=sales / max_sales,
                freshness=freshness_rank[row.id] / rank_denom,
            )
            for row, quality, sales in zip(rows, raw_quality, raw_sales)
        ]


class BookMainExplorationReco:
    def __init__(self, db_helper: DatabaseHelper):
        self._db_helper = db_helper

    async def get(
        self,
        limit: int,
        cursor: BookMainRecoCursorDTO,
        excluded_ids: list[int],
    ) -> tuple[list[int], int | None]:
        start_key = cursor.exploration_last_random_key

        if start_key is None:
            # random_key равномерен на [0, 2^63), а cursor.seed — 32-битный.
            # Голый seed всегда меньше почти всех random_key => старт был бы
            # у нижней границы и каждая сессия видела бы одни и те же книги.
            # Растягиваем сид на весь домен ключа детерминированно.
            start_key = random.Random(cursor.seed).getrandbits(63)

        rows = await self._query(start_key, limit, excluded_ids)

        if not rows:
            # wrap-around: дошли до конца random_key — начинаем сначала,
            # excluded_ids защищает от повторов в рамках сессии
            rows = await self._query(None, limit, excluded_ids)

        ids = [row.id for row in rows]
        next_key = rows[-1].random_key if rows else start_key

        return ids, next_key

    async def _query(
        self,
        after_key: int | None,
        limit: int,
        excluded_ids: list[int],
    ) -> list[Row]:
        stmt = (
            select(BookModel.id, BookModel.random_key)
            .where(BookModel.is_available.is_(True))
        )

        if excluded_ids:
            stmt = stmt.where(BookModel.id.not_in(excluded_ids))

        if after_key is not None:
            stmt = stmt.where(BookModel.random_key > after_key)

        stmt = stmt.order_by(BookModel.random_key.asc()).limit(limit)

        async with self._db_helper.session_factory() as session:
            result = await session.execute(stmt)
            return result.all()


NEW_RECO_CATEGORY_CAP = 2


class BookMainNewReco:
    def __init__(self, db_helper: DatabaseHelper):
        self._db_helper = db_helper

    async def get(
        self,
        limit: int,
        cursor: BookMainRecoCursorDTO,
        profile: UserRecoProfileDTO,
        excluded_ids: list[int],
        impressed_ids: set[int] | None = None,
    ) -> tuple[list[int], int | None]:
        impressed_ids = impressed_ids or set()

        stmt = select(
            BookModel.id,
            BookModel.category_id,
        ).where(BookModel.is_available.is_(True))

        if profile.top_categories:
            stmt = stmt.where(BookModel.category_id.in_(profile.top_categories))

        if cursor.new_last_id is not None:
            stmt = stmt.where(BookModel.id < cursor.new_last_id)

        stmt = stmt.order_by(BookModel.id.desc()).limit(limit * CANDIDATE_MULTIPLIER)

        async with self._db_helper.session_factory() as session:
            result = await session.execute(stmt)
            rows = result.all()

        excluded = set(excluded_ids)
        candidates = [row for row in rows if row.id not in excluded]

        # Сэмплируем внутри окна свежести, а не берём детерминированный
        # топ-limit: при статичном каталоге "новинки" иначе никогда
        # не ротируются — одни и те же книги на первой странице вечно.
        # Вес — свежесть (позиция) со штрафом за недавний показ.
        sample_weights = [
            (1.0 / (rank + 1))
            * (IMPRESSION_PENALTY if row.id in impressed_ids else 1.0)
            for rank, row in enumerate(candidates)
        ]
        sampled = _weighted_sample(
            items=candidates,
            weights=sample_weights,
            limit=len(candidates),
            seed=cursor.seed ^ cursor.page,
            key_fn=lambda row: row.id,
        )

        # Кап на категорию: свежезалитая пачка книг одной категории
        # не должна занимать все слоты новинок
        picked: list[int] = []
        category_counts: dict[int, int] = {}

        for row in sampled:
            if category_counts.get(row.category_id, 0) >= NEW_RECO_CATEGORY_CAP:
                continue
            picked.append(row.id)
            category_counts[row.category_id] = (
                category_counts.get(row.category_id, 0) + 1
            )
            if len(picked) >= limit:
                break

        if len(picked) < limit:
            picked_set = set(picked)
            for row in sampled:
                if row.id not in picked_set:
                    picked.append(row.id)
                    picked_set.add(row.id)
                if len(picked) >= limit:
                    break

        # Курсор двигаем только за реально показанные книги — иначе
        # непоказанный хвост окна выборки терялся бы для сессии навсегда.
        # Пропущенные капом книги с id выше min(picked) при этом теряются
        # для сессии осознанно: это и есть заливающая категория.
        next_id = min(picked) if picked else cursor.new_last_id

        random.Random(cursor.seed ^ cursor.page).shuffle(picked)

        return picked, next_id


class BookMainPopularReco:
    def __init__(
        self,
        db_helper: DatabaseHelper,
        cold_candidates: BookColdCandidatesProvider,
    ):
        self._db_helper = db_helper
        self._cold_candidates = cold_candidates

    async def get(
        self,
        limit: int,
        cursor: BookMainRecoCursorDTO,
        excluded_ids: list[int],
    ) -> tuple[list[int], tuple[float, int] | None]:
        # Скользящее окно популярности (см. popularity_window_subquery):
        # сумма дневных score за POPULARITY_WINDOW_DAYS дней от последней
        # доступной даты статистики — общий источник с каталогом.
        popularity = popularity_window_subquery()

        stmt = (
            select(
                BookModel.id,
                popularity.c.popularity_score,
            ).join(
                popularity,
                popularity.c.book_id == BookModel.id,
            ).where(
                BookModel.is_available.is_(True),
                popularity.c.popularity_score > 0,
            )
        )

        if (
            cursor.popular_last_score is not None
            and cursor.popular_last_book_id is not None
        ):
            stmt = stmt.where(
                or_(
                    popularity.c.popularity_score < cursor.popular_last_score,
                    and_(
                        popularity.c.popularity_score == cursor.popular_last_score,
                        BookModel.id < cursor.popular_last_book_id,
                    ),
                )
            )

        stmt = stmt.order_by(
            popularity.c.popularity_score.desc(),
            BookModel.id.desc(),
        ).limit(limit * WIDE_CANDIDATE_MULTIPLIER)

        async with self._db_helper.session_factory() as session:
            result = await session.execute(stmt)
            rows = result.all()

        if not rows and cursor.popular_last_score is None:
            # Статистики популярности ещё нет (job не отработал / холодная база) —
            # фолбэк на топ продаж, иначе источник молча пустеет
            logger.info("Popular: no popularity stats, falling back to total_sales")
            ids = await self._fallback_top_sales(limit, cursor, excluded_ids)
            return ids, None

        excluded = set(excluded_ids)
        candidates = [row for row in rows if row.id not in excluded]

        if not candidates:
            return [], None

        weights = [float(row.popularity_score) for row in candidates]
        sampled = _weighted_sample(
            items=candidates,
            weights=weights,
            limit=limit,
            seed=cursor.seed ^ cursor.page,
            key_fn=lambda row: row.id,
        )

        ids = [row.id for row in sampled]

        min_row = min(sampled, key=lambda row: (float(row.popularity_score), -row.id))
        next_cursor = (float(min_row.popularity_score), min_row.id)

        return ids, next_cursor

    async def _fallback_top_sales(
        self,
        limit: int,
        cursor: BookMainRecoCursorDTO,
        excluded_ids: list[int],
    ) -> list[int]:
        candidates = await self._cold_candidates.get()

        excluded = set(excluded_ids)
        pool = [c for c in candidates if c.id not in excluded]
        weights = [_cold_sales_weight(c) for c in pool]

        return _diversified_pick(
            candidates=pool,
            weights=weights,
            limit=limit,
            seed=cursor.seed ^ cursor.page ^ POPULAR_FALLBACK_SEED_SALT,
        )


ECHELON_SIZE = 10
PAGES_PER_ECHELON = 3
SIMILAR_USERS_LIMIT = 50

PERSONALIZED_QDRANT_OFFSET_LIMIT = 200

class BookPersonalizedReco:
    def __init__(
        self,
        db_helper: DatabaseHelper,
        books_qdrant_repo: BooksQdrantREPO,
        user_reco_profile_qdrant_repo: UserRecoProfileQdrantREPO,
        cold_candidates: BookColdCandidatesProvider,
    ):
        self._db_helper = db_helper
        self._books_qdrant = books_qdrant_repo
        self._user_reco_profile_qdrant = user_reco_profile_qdrant_repo
        self._cold_candidates = cold_candidates

    async def get(
        self,
        user_id: int,
        limit: int,
        cursor: BookMainRecoCursorDTO,
        profile: UserRecoProfileDTO,
        excluded_ids: list[int],
        impressed_ids: set[int] | None = None,
    ) -> tuple[list[int], BookPersonalizedRecoStatusDTO]:
        impressed_ids = impressed_ids or set()

        # Купленное не рекомендуем: после покупки вектор пользователя
        # смещается к этой книге сильнее всего (вес purchase = 3.0),
        # и без исключения она возвращается в топ рекомендаций.
        if profile.purchased_books:
            excluded_ids = list(dict.fromkeys(
                [*excluded_ids, *profile.purchased_books]
            ))

        vector = profile.vector

        if not vector:
            ids = await self._cold_start(
                limit, cursor, excluded_ids, profile, impressed_ids
            )

            return (
                ids,
                BookPersonalizedRecoStatusDTO(
                    mode="vector",
                    personalized_offset=0,
                    collaborative_offset=0,
                ),
            )

        if cursor.personalized_offset >= PERSONALIZED_QDRANT_OFFSET_LIMIT \
            or cursor.personalized_mode == "collaborative":
                return await self._fallback_to_collaborative(
                    user_id=user_id,
                    vector=vector,
                    limit=limit,
                    cursor=cursor,
                    excluded_ids=excluded_ids,
                    impressed_ids=impressed_ids,
                    personalized_offset=PERSONALIZED_QDRANT_OFFSET_LIMIT,
                )

        points = await self._books_qdrant.recommendations_for_user_profile(
            vector=vector,
            limit=limit * WIDE_CANDIDATE_MULTIPLIER,
            exclude_ids=excluded_ids or None,
        )

        if len(points) < limit:
            return await self._fallback_to_collaborative(
                user_id=user_id,
                vector=vector,
                limit=limit,
                cursor=cursor,
                excluded_ids=excluded_ids,
                impressed_ids=impressed_ids,
                personalized_offset=cursor.personalized_offset,
            )

        points = self._rerank(points, profile)

        ids = self._weighted_diversify(
            points,
            limit,
            seed=cursor.seed ^ cursor.page,
            impressed_ids=impressed_ids,
        )

        return (
            ids,
            BookPersonalizedRecoStatusDTO(
                mode="vector",
                personalized_offset=cursor.personalized_offset + limit,
                collaborative_offset=0,
            ),
        )

    async def _fallback_to_collaborative(
        self,
        user_id: int,
        vector: list[float],
        limit: int,
        cursor: BookMainRecoCursorDTO,
        excluded_ids: list[int],
        impressed_ids: set[int],
        personalized_offset: int,
    ) -> tuple[list[int], BookPersonalizedRecoStatusDTO]:
        """
            Общая точка перехода vector -> collaborative режим.
            Раньше дублировалась в двух местах get() с риском разойтись
            при будущих правках сигнатуры/статуса.
        """

        ids = await self._collaborative(
            user_id=user_id,
            vector=vector,
            limit=limit,
            exclude_ids=excluded_ids,
            impressed_ids=impressed_ids,
            seed=cursor.seed ^ cursor.page,
            collaborative_offset=cursor.collaborative_offset,
        )

        return ids, BookPersonalizedRecoStatusDTO(
            mode="collaborative",
            personalized_offset=personalized_offset,
            collaborative_offset=cursor.collaborative_offset + limit,
        )

    async def _collaborative(
        self,
        user_id: int,
        vector: list[float],
        limit: int,
        exclude_ids: list[int],
        impressed_ids: set[int],
        seed: int,
        collaborative_offset: int,
    ) -> list[int]:
        similar_users = await self._user_reco_profile_qdrant.find_similar_users(
            vector=vector,
            limit=SIMILAR_USERS_LIMIT,
            exclude_id=user_id,
        )

        if not similar_users:
            return []

        category_scores: dict[int, float] = {}

        for similar_user in similar_users:
            for rank, category_id in enumerate(similar_user.top_categories):
                position_weight = 1.0 / (rank + 1)
                category_scores[category_id] = (
                    category_scores.get(category_id, 0.0)
                    + similar_user.score * position_weight
                )

        if not category_scores:
            return []

        ranked_categories = sorted(
            category_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        collaborative_page = collaborative_offset // limit
        echelon = collaborative_page // PAGES_PER_ECHELON
        start = echelon * ECHELON_SIZE
        top_categories_slice = ranked_categories[start:start + ECHELON_SIZE]

        if not top_categories_slice:
            top_categories_slice = ranked_categories[:ECHELON_SIZE]

        top_categories = [cid for cid, _ in top_categories_slice]

        points = await self._books_qdrant.recommendations_for_user_profile(
            vector=vector,
            limit=limit * WIDE_CANDIDATE_MULTIPLIER,
            exclude_ids=exclude_ids,
            category_ids=top_categories,
        )

        weights = [
            max(p.score, 0.0)
            * (IMPRESSION_PENALTY if int(p.id) in impressed_ids else 1.0)
            for p in points
        ]
        sampled = _weighted_sample(
            items=points,
            weights=weights,
            limit=limit,
            seed=seed,
            key_fn=lambda p: int(p.id),
        )

        seen = set(exclude_ids)
        result: list[int] = []

        for point in sampled:
            book_id = int(point.id)

            if book_id not in seen:
                seen.add(book_id)
                result.append(book_id)

            if len(result) >= limit:
                break

        return result

    @staticmethod
    def _rerank(
        points: list[ScoredPoint],
        profile: UserRecoProfileDTO,
        category_boost: float = 0.15,
        author_boost: float = 0.10,
    ) -> list[ScoredPoint]:
        top_cats = set(profile.top_categories[:3])
        top_authors = set(profile.top_authors[:3])

        reranked = []
        for point in points:
            payload = point.payload or {}
            multiplier = 1.0
            if payload.get("category_id") in top_cats:
                multiplier += category_boost
            if payload.get("author_id") in top_authors:
                multiplier += author_boost

            reranked.append(
                point.model_copy(update={"score": point.score * multiplier})
            )

        reranked.sort(key=lambda p: p.score, reverse=True)
        return reranked

    def _weighted_diversify(
        self,
        points: list[ScoredPoint],
        limit: int,
        seed: int,
        impressed_ids: set[int] | None = None,
        category_cap: int = 2,
        author_cap: int = 2,
    ) -> list[int]:
        impressed_ids = impressed_ids or set()

        # Штраф за недавний показ: книга с топовым cosine-score иначе
        # сэмплируется почти всегда и не уходит с первой страницы
        weights = [
            max(p.score, 0.0)
            * (IMPRESSION_PENALTY if int(p.id) in impressed_ids else 1.0)
            for p in points
        ]
        sampled = _weighted_sample(
            items=points,
            weights=weights,
            limit=limit * CANDIDATE_MULTIPLIER,
            seed=seed,
            key_fn=lambda p: int(p.id),
        )

        category_counts: dict[int, int] = {}
        author_counts: dict[int, int] = {}
        result: list[int] = []
        seen_ids: set[int] = set()

        for point in sampled:
            if not point.payload:
                continue

            category_id = point.payload.get("category_id")
            author_id = point.payload.get("author_id")

            if category_id and category_counts.get(category_id, 0) >= category_cap:
                continue
            if author_id and author_counts.get(author_id, 0) >= author_cap:
                continue

            book_id = int(point.id)
            result.append(book_id)
            seen_ids.add(book_id)

            if category_id:
                category_counts[category_id] = category_counts.get(category_id, 0) + 1
            if author_id:
                author_counts[author_id] = author_counts.get(author_id, 0) + 1
            if len(result) >= limit:
                break

        if len(result) < limit:
            for point in sampled:
                if not point.payload:
                    continue
                book_id = int(point.id)
                if book_id not in seen_ids:
                    result.append(book_id)
                    seen_ids.add(book_id)
                if len(result) >= limit:
                    break
        
        logger.info(
            "WeightedDiversify: candidates=%d sampled=%d result=%d",
            len(points),
            len(sampled),
            len(result),
        )

        return result

    async def _cold_start(
        self,
        limit: int,
        cursor: BookMainRecoCursorDTO,
        excluded_ids: list[int],
        profile: UserRecoProfileDTO,
        impressed_ids: set[int],
    ) -> list[int]:
        """
            Нет вектора. Если у профиля уже есть категории (первые события
            пришли, вектор ещё не построен) — топ внутри этих категорий.
            Совсем новый пользователь — глобальный кэшированный пул
            с байесовским рейтингом, новизной и капами на категорию/автора.
        """

        if profile.top_categories:
            return await self._cold_start_by_categories(
                limit=limit,
                cursor=cursor,
                excluded_ids=excluded_ids,
                category_ids=profile.top_categories,
                impressed_ids=impressed_ids,
            )

        candidates = await self._cold_candidates.get()

        excluded = set(excluded_ids)
        pool = [c for c in candidates if c.id not in excluded]
        weights = [
            _cold_quality_weight(c)
            * (IMPRESSION_PENALTY if c.id in impressed_ids else 1.0)
            for c in pool
        ]

        return _diversified_pick(
            candidates=pool,
            weights=weights,
            limit=limit,
            seed=cursor.seed ^ cursor.page,
        )

    async def _cold_start_by_categories(
        self,
        limit: int,
        cursor: BookMainRecoCursorDTO,
        excluded_ids: list[int],
        category_ids: list[int],
        impressed_ids: set[int],
    ) -> list[int]:
        stmt = (
            select(BookModel.id)
            .where(
                BookModel.is_available.is_(True),
                BookModel.category_id.in_(category_ids),
            )
            .order_by(
                BookModel.rating.desc().nulls_last(),
                BookModel.total_sales.desc().nulls_last(),
                # random_key, не id: без рейтингов и продаж сортировка
                # по id отдавала бы только последние добавленные книги
                BookModel.random_key.asc(),
            )
            .limit(limit * CANDIDATE_MULTIPLIER)
        )

        async with self._db_helper.session_factory() as session:
            result = await session.execute(stmt)
            all_ids = [row[0] for row in result.all()]

        excluded = set(excluded_ids)
        candidates = [bid for bid in all_ids if bid not in excluded]

        # Вес по позиции, а не срез топа — иначе каждая сессия
        # видит одни и те же первые limit книг
        weights = [
            (1.0 / (rank + 1))
            * (IMPRESSION_PENALTY if bid in impressed_ids else 1.0)
            for rank, bid in enumerate(candidates)
        ]

        return _weighted_sample(
            items=candidates,
            weights=weights,
            limit=limit,
            seed=cursor.seed ^ cursor.page,
            key_fn=lambda bid: bid,
        )
    

class FeedSlot(StrEnum):
    PERSONALIZED = "personalized"
    POPULAR      = "popular"
    NEW          = "new"
    EXPLORATION  = "exploration"


# Состав страницы фида. Порядок слотов всё равно шаффлится по seed^page,
# поэтому важны только пропорции — счётчики честнее ручного паттерна.
SLOT_COUNTS: dict[FeedSlot, int] = {
    FeedSlot.PERSONALIZED: 8,
    FeedSlot.POPULAR: 6,
    FeedSlot.NEW: 4,
    FeedSlot.EXPLORATION: 2,
}


class BookMainRecoBlender:
    """
        Собирает финальный список book_id по SLOT_COUNTS.
        Порядок слотов шаффлится по seed^page — разный на каждой странице и сессии.
        Если источник исчерпан — слот заполняется из fallback-цепочки:
        personalized → popular → new → exploration.
    """

    _FALLBACK_ORDER = [
        FeedSlot.PERSONALIZED,
        FeedSlot.POPULAR,
        FeedSlot.NEW,
        FeedSlot.EXPLORATION,
    ]

    def mix(
        self,
        slots: BookBlenderSlotsDTO,
        seed: int,
        page: int
    ) -> list[int]:
        pattern = [
            slot
            for slot, count in SLOT_COUNTS.items()
            for _ in range(count)
        ]
        random.Random(seed ^ page).shuffle(pattern)

        queues: dict[FeedSlot, deque[int]] = {
            FeedSlot.PERSONALIZED: deque(slots.personalized),
            FeedSlot.POPULAR:      deque(slots.popular),
            FeedSlot.NEW:          deque(slots.new),
            FeedSlot.EXPLORATION:  deque(slots.exploration),
        }

        result: list[int] = []
        seen: set[int] = set()

        for slot in pattern:
            book_id = self._pop_from(slot, queues, seen)
            
            if book_id is not None:
                result.append(book_id)
                seen.add(book_id)

        return result

    def _pop_from(
        self,
        preferred: FeedSlot,
        queues: dict[FeedSlot, deque[int]],
        seen: set[int],
    ) -> int | None:
        order = [preferred] + [s for s in self._FALLBACK_ORDER if s != preferred]

        for slot in order:
            queue = queues[slot]
            while queue:
                candidate = queue.popleft()
                if candidate not in seen:
                    return candidate

        return None


PAGE_SIZE = sum(SLOT_COUNTS.values())
PERSONALIZED_LIMIT = SLOT_COUNTS[FeedSlot.PERSONALIZED]
POPULAR_LIMIT = SLOT_COUNTS[FeedSlot.POPULAR]
NEW_LIMIT = SLOT_COUNTS[FeedSlot.NEW]
EXPLORATION_LIMIT = SLOT_COUNTS[FeedSlot.EXPLORATION]


class BooksMainRecommendationsQH:
    def __init__(
        self,
        user_reco_profile: UserPersonalBooksRecoProfile,
        book_repository: BookSQLAlchemyREPO,
        book_reco_session: BookMainRecoSeenSession,
        personalized: BookPersonalizedReco,
        popular: BookMainPopularReco,
        new: BookMainNewReco,
        exploration: BookMainExplorationReco,
        blender: BookMainRecoBlender,
    ):
        self._user_reco_profile = user_reco_profile
        self._book_repo = book_repository
        self._book_reco_session = book_reco_session
        self._personalized  = personalized
        self._popular = popular
        self._new_books = new
        self._exploration = exploration
        self._blender = blender

    async def for_user(
        self,
        user_id: int,
        encoded_cursor: str | None = None,
    ) -> BookRecommendationsDTO:
        if encoded_cursor:
            cursor = BookMainRecoCursorDTO.decode(encoded_cursor)
            excluded_ids = await self._book_reco_session.get(cursor.session_id)
        else:
            await self._book_reco_session.ensure_new_session_allowed(user_id)

            session_id = self._book_reco_session.new_session_id()
            cursor = BookMainRecoCursorDTO.initial(
                seed=random.getrandbits(32),
                session_id=session_id,
            )
            excluded_ids = []

        log_ctx = {
            "user_id": user_id,
            "session_id": cursor.session_id,
            "page": cursor.page,
        }

        user_reco_profile = await self._user_reco_profile.get(
            user_id=user_id
        )

        impressed_ids = await self._book_reco_session.get_impressions(user_id)

        results = await asyncio.gather(
            self._personalized.get(user_id, PERSONALIZED_LIMIT, cursor, user_reco_profile, excluded_ids, impressed_ids),
            self._popular.get(POPULAR_LIMIT, cursor, excluded_ids),
            self._new_books.get(NEW_LIMIT, cursor, user_reco_profile, excluded_ids, impressed_ids),
            self._exploration.get(EXPLORATION_LIMIT, cursor, excluded_ids),
            return_exceptions=True,
        )

        source_names = ("personalized", "popular", "new", "exploration")

        unchanged_popular_cursor = (
            (cursor.popular_last_score, cursor.popular_last_book_id)
            if cursor.popular_last_score is not None
            and cursor.popular_last_book_id is not None
            else None
        )

        defaults = (
            ([], BookPersonalizedRecoStatusDTO(
                mode=cursor.personalized_mode,
                personalized_offset=cursor.personalized_offset,
                collaborative_offset=cursor.collaborative_offset,
            )),
            ([], unchanged_popular_cursor),
            ([], cursor.new_last_id),
            ([], cursor.exploration_last_random_key),
        )

        safe_results = []

        for name, result, default in zip(source_names, results, defaults):
            if isinstance(result, asyncio.CancelledError):
                # Отмену запроса нельзя глотать как деградацию источника
                raise result

            if isinstance(result, BaseException):
                logger.error(
                    "Feed source '%s' failed, falling back to empty + unchanged cursor state",
                    name,
                    exc_info=result,
                    extra=log_ctx,
                )
                safe_results.append(default)
            else:
                safe_results.append(result)

        (
            (personalized_ids, personalized_state),
            (popular_ids, popular_cursor),
            (new_ids, new_cursor),
            (exploration_ids, exploration_cursor),
        ) = safe_results

        logger.info(
            "Feed sources: personalized=%d popular=%d new=%d exploration=%d",
            len(personalized_ids),
            len(popular_ids),
            len(new_ids),
            len(exploration_ids),
            extra=log_ctx,
        )

        merged_ids = self._blender.mix(
            BookBlenderSlotsDTO(
                personalized=personalized_ids,
                popular=popular_ids,
                new=new_ids,
                exploration=exploration_ids,
            ),
            seed=cursor.seed,
            page=cursor.page,
        )

        if not merged_ids:
            return BookRecommendationsDTO(books=[], next_cursor=None)

        books_unordered = await self._book_repo.get_preview_by_ids(merged_ids)
        book_map = {b.id: b for b in books_unordered}
        books = [book_map[bid] for bid in merged_ids if bid in book_map]

        # Атомарный append (RPUSH), merge и trim делает сам seen-session
        await self._book_reco_session.add(cursor.session_id, merged_ids)
        await self._book_reco_session.add_impressions(user_id, merged_ids)

        next_cursor_obj = BookMainRecoCursorDTO(
            session_id=cursor.session_id,
            seed=cursor.seed,
            page=cursor.page + 1,
            personalized_mode=personalized_state.mode,
            personalized_offset=personalized_state.personalized_offset,
            collaborative_offset=personalized_state.collaborative_offset,
            popular_last_score=(
                popular_cursor[0] if popular_cursor else cursor.popular_last_score
            ),
            popular_last_book_id=(
                popular_cursor[1] if popular_cursor else cursor.popular_last_book_id
            ),
            new_last_id=new_cursor,
            exploration_last_random_key=exploration_cursor,
        )

        return BookRecommendationsDTO(
            books=books,
            next_cursor=next_cursor_obj.encode() if books else None,
        )