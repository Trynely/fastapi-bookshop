import logging
from app.client.api.events.user.personal_reco import UserPersonalRecoEVENT
from app.client.db.postgres.repositories.sqlalchemy.user_event import UserEventSQLAlchemyREPO
from app.client.service.infrastructure.taskiq.schedules.user.base import IUserSchedulesPublisher
from app.client.service.infrastructure.user.reco_profile import UserPersonalBooksRecoProfileCache, UserRecoKeys
from app.core.config.client.user.personal_book_reco import VECTOR_FLAG_TTL
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.redis.clients import RedisClient
from app.client.db.postgres.models import USER_EVENT_WEIGHTS, UserEventENUM, UserEventModel
from app.shared.service.infrastructure.redis.clients import RedisClient

logger = logging.getLogger(__name__)

EVENT_VERSION_TTL = 86400 * 30 # 30 days

class BookPersonalRecoForUserUC:
    def __init__(
        self,
        redis: RedisClient,
        user_profile_cache: UserPersonalBooksRecoProfileCache,
        transaction: SQLAlchemyTransaction,
        book_repository: BookSQLAlchemyREPO,
        user_event_repository: UserEventSQLAlchemyREPO,
        schedule_publisher: IUserSchedulesPublisher,
    ):
        self._redis = redis
        self._transaction = transaction
        self._schedule_publisher = schedule_publisher
        self.user_profile_cache = user_profile_cache
        self.book_repository = book_repository
        self.user_event_repository = user_event_repository
 
    async def generate(self, event: UserPersonalRecoEVENT) -> None:
        """Обрабатывает входящее пользовательское событие для персональных рекомендаций.

        Последовательность действий:
        1. Пропускает дубликат события просмотра (VIEW).
        2. В транзакции получает метаданные книги (category_id, author_id), вычисляет вес
            события и сохраняет событие в БД (UserEventModel).
        3. Логирует и пробрасывает исключения при неудаче сохранения.
        4. Выполняет пост-обработку: инвалидирует кэш профиля пользователя, чтобы
            следующий запрос профиля пересобрал его из БД с учётом нового события.
        """
        
        if await self._is_duplicate_view(event):
            logger.info("Duplicate VIEW skipped")
            return

        try:
            async with self._transaction:
                category_id, author_id = await self._book_meta(event)

                event_weight = self._calculate_event_weight(
                    event_type=event.type,
                    meta=event.metadata,
                    user_id=event.user_id,
                )

                user_db_event = UserEventModel(
                    user_id=event.user_id,
                    book_id=event.book_id,
                    event_type=event.type,
                    metada=event.metadata,
                    category_id=category_id,
                    author_id=author_id,
                    weight=event_weight,
                )
                await self.user_event_repository.save(
                    user_db_event
                )
                
                logger.info("Event saved in UserEventModel")
        except Exception:
            logger.exception(
                "Failed to save event in UserEventModel",
                extra={
                    "user_id": event.user_id,
                    "book_id": event.book_id,
                    "event_type": event.type.value,
                },
            )
            raise

        try:
            await self.user_profile_cache.invalidate(event.user_id)
        except Exception:
            logger.exception(
                "Failed to invalidate profile cache",
                extra={"user_id": event.user_id},
            )

        try:
            await self._update_user_reco_profile(event.user_id)
        except Exception:
            logger.exception(
                "Failed to schedule vector update",
                extra={"user_id": event.user_id},
            )

    async def _is_duplicate_view(self, event: UserPersonalRecoEVENT) -> bool:
        """Проверяет, является ли событие VIEW по книге дубликатом.

        Для событий VIEW с book_id метод пытается создать ключ дедупликации в Redis,
        уникальный для пары (user_id, book_id), с коротким TTL (60 секунд). Если ключ
        уже существует, просмотр считается дубликатом и метод возвращает True.
        Для событий, отличных от VIEW, или событий без book_id метод всегда возвращает False.
        """

        if (
            event.type != UserEventENUM.VIEW
            or not event.book_id
        ):
            return False
        
        view_dedup_key = (
            f"event_dedup:"
            f"{event.user_id}:"
            f"{event.book_id}:view"
        )

        key_created = await self._redis.string.add(
            view_dedup_key,
            1,
            ex=60,
            nx=True,
        )

        return not key_created
    
    async def _book_meta(
        self,
        event: UserPersonalRecoEVENT,
    ) -> tuple[int | None, int | None]:
        """Получить meta-информацию о книге из события.

        Возвращает кортеж (category_id, author_id) для книги, указанной в event.book_id.
        Если event.book_id отсутствует или книга не найдена в репозитории,
        возвращает (None, None). В случае отсутствия книги метод также
        логирует предупреждение с идентификаторами book_id и user_id.
        """
        
        if not event.book_id:
            return None, None

        book = await self.book_repository.get_category_and_author_id_by_book_id(
            book_id=event.book_id
        )

        if not book:
            logger.warning(
                "Book not found while processing event",
                extra={
                    "book_id": event.book_id,
                    "user_id": event.user_id,
                },
            )

            return None, None
        return book.category_id, book.author_id
    
    def _calculate_event_weight(
        self,
        event_type: UserEventENUM,
        meta: dict,
        user_id: int | None = None,
    ) -> float:
        """
            Вычисляет вес пользовательского события.

            Параметры:
            - event_type: тип события (например, VIEW, CLICK, RATING и т.д.).
            - meta: дополнительная мета-информация события (для RATING ожидается поле "rating").
            - user_id: опциональный идентификатор пользователя для логирования.

            Поведение:
            - Для всех типов берётся базовый вес из USER_EVENT_WEIGHTS, по умолчанию 0.5.
            - Для события типа RATING пытается извлечь значение рейтинга из meta:
                - если поле отсутствует или не может быть приведено к float — логирует предупреждение
                    и возвращает 0.0.
                - в противном случае вычисляет вес как (rating - 3.0) * 0.75.

            Возвращает вычисленное вещественное значение веса.
        """

        weight = USER_EVENT_WEIGHTS.get(event_type, 0.5)

        if event_type == UserEventENUM.RATING:
            rating_value = meta.get("rating")

            if rating_value is None:
                logger.warning(
                    "RATING event missing rating field",
                    extra={"user_id": user_id},
                )
                return 0.0

            try:
                rating_value = float(rating_value)
            except (TypeError, ValueError):
                logger.warning(
                    "Invalid rating value",
                    extra={
                        "user_id": user_id,
                        "rating": rating_value,
                    },
                )
                return 0.0
            
            weight = (rating_value - 3.0) * 0.75
        return weight

    async def _update_user_reco_profile(self, user_id: int) -> None:
        """
            Обновляет счётчик версии рекомендаций пользователя и ставит флаг ожидания.

            Увеличивает ключ версии в Redis, пытается установить временный флаг pending
            для обозначения необходимости пересчёта векторных рекомендаций. Если флаг
            устанавливается впервые — планирует отложенную задачу обновления вектора.
            Если флаг уже существует — продлевает его TTL; при неудаче продления
            логирует предупреждение.
        """

        version_key = UserRecoKeys.version(user_id)
        pending_key = UserRecoKeys.pending(user_id)

        await self._redis.string.incr(version_key)
        await self._redis.key.expire(version_key, EVENT_VERSION_TTL)

        is_new = await self._redis.string.add(
            pending_key,
            1,
            ex=VECTOR_FLAG_TTL,
            nx=True,
        )

        if is_new:
            logger.info("Starting user recommendation profile update...")

            await self._schedule_publisher.update_user_reco_profile(
                user_id=user_id
            )
        else:
            extended = await self._redis.key.expire(
                pending_key,
                VECTOR_FLAG_TTL,
            )

            if not extended:
                logger.warning(
                    "Failed to extend pending flag ttl",
                    extra={"user_id": user_id},
                )