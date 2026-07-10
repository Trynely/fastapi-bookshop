import json
import logging
import math
import numpy as np
from collections import defaultdict
from datetime import datetime, timezone
from heapq import nlargest
from app.client.db.postgres.models import UserEventENUM
from app.client.db.postgres.repositories.sqlalchemy.user_event import (
    UserEventSQLAlchemyREPO,
)
from app.client.db.qdrant.repositories.user.reco_profile import UserRecoProfileQdrantREPO
from app.client.dto.user.reco_profile import UserRecoProfileDTO
from app.client.dto.user.qdrant_reco_profile_payload import UserRecoProfileQdrantPayloadDTO
from app.client.service.infrastructure.taskiq.schedules.user.base import IUserSchedulesPublisher
from app.core.config.client.user.personal_book_reco import (
    MAX_INTERACTED_BOOKS_FOR_VECTOR,
    VECTOR_FLAG_TTL,
    VECTOR_LOCK_TTL,
)
from app.product.db.postgres.repositories.sqlalchemy.author import (
    BookAuthorSQLAlchemyREPO,
)
from app.product.db.postgres.repositories.sqlalchemy.book import (
    BookSQLAlchemyREPO,
)
from app.product.db.postgres.repositories.sqlalchemy.category import (
    BookCategorySQLAlchemyREPO,
)
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.shared.dto.qdrant_point import QdrantPointDTO
from app.shared.service.infrastructure.base import json_to_dict
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder
from app.shared.service.infrastructure.redis.clients import RedisClient

logger = logging.getLogger(__name__)

PROFILE_TTL = 3600
RECS_TTL = 900
INTERACTION_TTL = 86400 * 30  # 30 days
RECOMMENDATION_CACHE_VERSION = "v1"

DECAY_DAYS = 30
TOP_CATEGORIES_LIMIT = 5
TOP_AUTHORS_LIMIT = 5
SEARCH_HISTORY_LIMIT = 10

VECTOR_WEIGHT_BOOKS = 0.7
VECTOR_WEIGHT_PROFILE = 0.3


class UserRecoKeys:
    @staticmethod
    def pending(user_id: int) -> str:
        return f"user_reco:{user_id}:pending"

    @staticmethod
    def lock(user_id: int) -> str:
        return f"user_reco:{user_id}:lock"

    @staticmethod
    def version(user_id: int) -> str:
        return f"user_reco:{user_id}:version"


class UserRecoProfileEmbeddingTextBuilder:
    def execute(self, profile: UserRecoProfileQdrantPayloadDTO) -> str:
        parts = []

        if profile.top_authors:
            parts.append("Авторы: " + ", ".join(profile.top_authors))

        if profile.top_categories:
            parts.append("Категории: " + ", ".join(profile.top_categories))

        if profile.recent_searches:
            parts.append("Поиски: " + ", ".join(profile.recent_searches))

        if profile.descriptions:
            parts.append("Темы книг: " + " | ".join(profile.descriptions))

        return ". ".join(parts)


class UserProfileUpdateProcess:
    def __init__(
        self,
        redis: RedisClient,
    ):
        self._redis = redis

    async def acquire_lock(
        self,
        user_id: int,
    ) -> bool:
        return await self._redis.string.add(
            UserRecoKeys.lock(user_id),
            1,
            ex=VECTOR_LOCK_TTL,
            nx=True,
        )

    async def release_lock(
        self,
        user_id: int,
    ) -> None:
        await self._redis.key.remove(
            UserRecoKeys.lock(user_id)
        )

    async def has_pending(
        self,
        user_id: int,
    ) -> bool:
        return await self._redis.key.exists(
            UserRecoKeys.pending(user_id)
        )

    async def create_pending(
        self,
        user_id: int,
    ) -> bool:
        return await self._redis.string.add(
            UserRecoKeys.pending(user_id),
            1,
            ex=VECTOR_FLAG_TTL,
            nx=True,
        )

    async def remove_pending(
        self,
        user_id: int,
    ) -> None:
        await self._redis.key.remove(
            UserRecoKeys.pending(user_id)
        )

    async def get_version(
        self,
        user_id: int,
    ) -> int:
        value = await self._redis.string.get(
            UserRecoKeys.version(user_id)
        )

        return int(value or 0)

    async def increment_version(
        self,
        user_id: int,
    ) -> int:
        return await self._redis.string.incr(
            UserRecoKeys.version(user_id)
        )


class UserPersonalBooksRecoProfileCache:
    def __init__(self, redis: RedisClient):
        self._redis = redis

    @staticmethod
    def _profile_key(user_id: int) -> str:
        return f"user_reco_profile:{user_id}"

    @staticmethod
    def _vector_key(user_id: int) -> str:
        return f"user_reco_vector:{user_id}"

    async def get_profile(
        self,
        user_id: int,
    ) -> dict | None:
        raw = await self._redis.string.get(
            self._profile_key(user_id)
        )

        return json_to_dict(raw) if raw else None

    async def set_profile(
        self,
        user_id: int,
        profile: dict,
    ) -> None:
        await self._redis.string.add(
            self._profile_key(user_id),
            profile,
            ex=PROFILE_TTL,
        )

    async def get_vector(
        self,
        user_id: int,
    ) -> list[float] | None:
        raw = await self._redis.string.get(
            self._vector_key(user_id)
        )

        if not raw:
            return None

        return json.loads(raw)

    async def set_vector(
        self,
        user_id: int,
        vector: list[float],
    ) -> None:
        await self._redis.string.add(
            self._vector_key(user_id),
            json.dumps(vector),
            ex=PROFILE_TTL,
        )

    async def invalidate(
        self,
        user_id: int,
    ) -> None:
        await self._redis.key.remove(
            self._profile_key(user_id),
            self._vector_key(user_id),
        )


class UserPersonalBooksRecoProfile:
    def __init__(
        self,
        embedder: OllamaEmbedder,
        user_profile_cache: UserPersonalBooksRecoProfileCache,
        user_event_repository: UserEventSQLAlchemyREPO,
        book_repository: BookSQLAlchemyREPO,
        book_author_repository: BookAuthorSQLAlchemyREPO,
        book_category_repository: BookCategorySQLAlchemyREPO,
        schedule_publisher: IUserSchedulesPublisher,
        user_reco_profile_qdrant_repo: UserRecoProfileQdrantREPO,
        books_qdrant_repo: BooksQdrantREPO,
        user_profile_update_process: UserProfileUpdateProcess,
        user_reco_embed_text: UserRecoProfileEmbeddingTextBuilder,
    ):
        self._embedder = embedder
        self._schedule_publisher = schedule_publisher
        self.user_reco_embed_text = user_reco_embed_text
        self.user_profile_cache = user_profile_cache
        self.user_event_repository = user_event_repository
        self.book_repository = book_repository
        self.book_author_repository = book_author_repository
        self.book_category_repository = book_category_repository
        self.user_reco_profile_qdrant_repo = user_reco_profile_qdrant_repo
        self.books_qdrant_repo = books_qdrant_repo
        self.user_profile_update_process = user_profile_update_process

    async def get(self, user_id: int) -> UserRecoProfileDTO:
        user_profile_cached = await self.user_profile_cache.get_profile(user_id)

        if user_profile_cached:
            dto = UserRecoProfileDTO(**user_profile_cached)
        else:
            # 2. Строим профиль из событий
            user_events = await self.user_event_repository.get_list_by_user_id_by_new(
                user_id=user_id,
            )

            category_scores = defaultdict(float)
            author_scores = defaultdict(float)
            recent_searches: list[str] = []
            interacted_books: list[int] = []
            purchased_books: list[int] = []
            seen_books: set[int] = set()
            seen_purchased: set[int] = set()

            now = datetime.now(timezone.utc)

            for event in user_events:
                if (
                    event.book_id
                    and event.book_id not in seen_books
                ):
                    interacted_books.append(event.book_id)
                    seen_books.add(event.book_id)

                if (
                    event.book_id
                    and event.event_type == UserEventENUM.PURCHASE
                    and event.book_id not in seen_purchased
                ):
                    purchased_books.append(event.book_id)
                    seen_purchased.add(event.book_id)

                age_days = max(
                    (now - event.created_at).days,
                    0,
                )

                decay = math.exp(-age_days / DECAY_DAYS)
                weighted_score = event.weight * decay

                if event.category_id:
                    category_scores[event.category_id] += weighted_score

                if event.author_id:
                    author_scores[event.author_id] += weighted_score

                if event.event_type == UserEventENUM.SEARCH:
                    query = event.metada.get("query")

                    if (
                        query
                        and query not in recent_searches
                    ):
                        recent_searches.append(query)

            top_categories = nlargest(
                TOP_CATEGORIES_LIMIT,
                category_scores.keys(),
                key=category_scores.get,
            )

            top_authors = nlargest(
                TOP_AUTHORS_LIMIT,
                author_scores.keys(),
                key=author_scores.get,
            )

            profile = {
                "user_id": user_id,
                "top_categories": top_categories,
                "top_authors": top_authors,
                "category_scores": dict(category_scores),
                "author_scores": dict(author_scores),
                "recent_searches": recent_searches[:SEARCH_HISTORY_LIMIT],
                "interacted_books": interacted_books,
                "purchased_books": purchased_books,
            }

            await self.user_profile_cache.set_profile(user_id, profile)

            dto = UserRecoProfileDTO(**profile)

        # 3. Подтягиваем вектор: Redis → Qdrant
        vector = await self.user_profile_cache.get_vector(user_id)

        if vector is None:
            points = await self.user_reco_profile_qdrant_repo.get(
                point_ids=[user_id],
                with_vectors=True,
            )

            if points:
                vector = points[0].vector

                # Прогреваем Redis-кэш чтобы не ходить в Qdrant каждый раз
                if vector:
                    await self.user_profile_cache.set_vector(user_id, vector)

        return UserRecoProfileDTO(
            user_id=dto.user_id,
            top_categories=dto.top_categories,
            top_authors=dto.top_authors,
            category_scores=dto.category_scores,
            author_scores=dto.author_scores,
            recent_searches=dto.recent_searches,
            interacted_books=dto.interacted_books,
            purchased_books=dto.purchased_books,
            vector=vector,
        )

    async def _update_profile(self, user_id: int) -> None:
        profile = await self.get(user_id=user_id)
        interacted = profile.interacted_books[:MAX_INTERACTED_BOOKS_FOR_VECTOR]

        if not interacted:
            return

        book_points = await self.books_qdrant_repo.get(
            point_ids=interacted,
            with_vectors=True,
        )

        if not book_points:
            return

        book_weights = await self.user_event_repository.get_weights_by_book(
            user_id=user_id,
            book_ids=interacted,
        )

        weights_map = {
            row.book_id: max(
                min(float(row.total_weight), 3.0),
                0.1,
            )
            for row in book_weights
        }

        vectors = []
        weights = []

        for point in book_points:
            if not point.vector:
                continue

            vectors.append(point.vector)
            weights.append(
                weights_map.get(point.id, 0.1)
            )

        if not vectors:
            return

        vectors_np = np.array(vectors, dtype=np.float32)
        weights_np = np.array(weights, dtype=np.float32)

        avg_vector = np.average(
            vectors_np,
            axis=0,
            weights=weights_np,
        )

        authors = await self.book_author_repository.get_by_ids(
            author_ids=profile.top_authors
        )

        author_names = {
            row.id: row.name
            for row in authors
        }

        categories = await self.book_category_repository.get_by_ids(
            category_ids=profile.top_categories
        )

        category_names = {
            category.id: category.title
            for category in categories
        }

        book_db_descriptions = (
            await self.book_repository.get_descriptions_by_ids(
                book_ids=interacted,
                limit=5,
            )
        )

        books_descriptions = [
            desc[:300]
            for desc in book_db_descriptions
            if desc
        ]

        user_recot_profile_payload = UserRecoProfileQdrantPayloadDTO(
            top_authors=[
                author_names.get(a, str(a))
                for a in profile.top_authors
            ],
            top_categories=[
                category_names.get(c, str(c))
                for c in profile.top_categories
            ],
            recent_searches=profile.recent_searches,
            descriptions=books_descriptions,
        )

        text_vector = await self._embedder.embed(
            self.user_reco_embed_text.execute(
                user_recot_profile_payload
            )
        )

        text_vector_np = np.array(text_vector, dtype=np.float32)

        final_vector = (
            avg_vector * VECTOR_WEIGHT_BOOKS
            + text_vector_np * VECTOR_WEIGHT_PROFILE
        )

        norm = np.linalg.norm(final_vector)

        if norm > 0:
            final_vector /= norm

        final_vector_list = final_vector.tolist()

        # Сохраняем вектор в Redis-кэш сразу после построения
        await self.user_profile_cache.set_vector(user_id, final_vector_list)

        await self.user_reco_profile_qdrant_repo.save(
            QdrantPointDTO(
                id=user_id,
                vector=final_vector_list,
                payload={
                    "top_categories": profile.top_categories,
                    "top_authors": profile.top_authors,
                },
            )
        )

    async def _rebuild(
        self,
        start_version: int,
        end_version: int,
        user_id: int,
    ) -> None:
        logger.info(
            "New events arrived during vector update",
            extra={
                "user_id": user_id,
                "start_version": start_version,
                "end_version": end_version,
            },
        )

        pending_created = (
            await self.user_profile_update_process.create_pending(
                user_id=user_id,
            )
        )

        if pending_created:
            await self._schedule_publisher.update_user_reco_profile(
                user_id=user_id,
            )

    async def build(
        self,
        user_id: int,
    ) -> None:
        is_locked = (
            await self.user_profile_update_process.acquire_lock(
                user_id=user_id,
            )
        )

        if not is_locked:
            logger.info(
                "Vector update already running",
                extra={"user_id": user_id},
            )
            return

        try:
            pending_exists = (
                await self.user_profile_update_process.has_pending(
                    user_id=user_id,
                )
            )

            if not pending_exists:
                logger.info(
                    "Pending flag not found",
                    extra={"user_id": user_id},
                )
                return

            start_version = (
                await self.user_profile_update_process.get_version(
                    user_id=user_id,
                )
            )

            await self._update_profile(user_id=user_id)

            end_version = (
                await self.user_profile_update_process.get_version(
                    user_id=user_id,
                )
            )

            await self.user_profile_update_process.remove_pending(
                user_id=user_id,
            )

            if end_version != start_version:
                await self._rebuild(
                    start_version=start_version,
                    end_version=end_version,
                    user_id=user_id,
                )

            logger.info(
                "user reco vector update is done",
                extra={"user_id": user_id},
            )

        except Exception:
            logger.exception(
                "Failed to update vector",
                extra={"user_id": user_id},
            )
            raise

        finally:
            await self.user_profile_update_process.release_lock(
                user_id=user_id,
            )