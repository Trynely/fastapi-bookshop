from sqlalchemy import Select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, contains_eager, selectinload
from app.product.api.requests.filter_by_similar import FilterSimilarBooksREQT
from typing import List, Optional
from app.product.db.postgres.models.book import BookModel, BookPopularityStatsModel
from app.product.db.postgres.models.category import BookCategoryModel
from app.product.db.postgres.repositories.sqlalchemy.paginators.book.cursor import BookSQLAlchemyCursorPaginator
from app.product.dto.book.elastic_document import BookElasticDocumentDTO
from app.product.dto.book.qdrant_payload import BooksQdrantPayloadDTO
from app.shared.api.requests.cursor_pagintaion import (
    CursorEncodedPaginationREQT,
    CursorMD5RandomPaginationREQT,
    CursorIDPaginationREQT,
)
from app.shared.db.postgres.repositories.sqlalchemy.repository import BaseSQLAlchemyREPO
from app.shared.dto.cursor_pagination import CursorPaginationDTO
from app.order.db.models.wishlist import WishlistModel

class BookSQLAlchemyREPO(BaseSQLAlchemyREPO[BookModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(
            session=session,
            model=BookModel
        )
        self._paginator = BookSQLAlchemyCursorPaginator(session=session)

    def _with_relations(self, stmt: Select) -> Select:
        return stmt.options(
            joinedload(self.model.category),
            joinedload(self.model.author),
            joinedload(self.model.paper_type),
            joinedload(self.model.made_in),
        )
    
    def _base_query(self):
        return self._with_relations(select(self.model))
        
    async def get_list_by_new(
        self,
        pagination: Optional[CursorIDPaginationREQT] = None
    ) -> CursorPaginationDTO:
        stmt = self._base_query().order_by(self.model.id.desc())
        return await self._paginator.paginate_new(stmt, pagination.id_cursor)
    
    async def get_list_by_popular(
        self,
        pagination: Optional[CursorEncodedPaginationREQT] = None,
    ) -> CursorPaginationDTO:
        # Последняя доступная дата статистики, а не жёстко "вчера" —
        # если job пересчёта пропустил день, выдача не пустеет
        # (симметрично BookMainPopularReco в main_reco.py).
        latest_stat_date = select(
            func.max(BookPopularityStatsModel.stat_date)
        ).scalar_subquery()

        stmt = (
            select(
                self.model,
                BookPopularityStatsModel.popularity_score,
            )
            # INNER JOIN — намеренно: книги без статистики (новые / без активности)
            # не попадают в "популярное". Если нужно иначе — outerjoin + coalesce.
            .join(
                BookPopularityStatsModel,
                BookPopularityStatsModel.book_id == self.model.id,
            )
            .where(
                self.model.is_available.is_(True),
                BookPopularityStatsModel.stat_date == latest_stat_date,
            )
            .order_by(
                BookPopularityStatsModel.popularity_score.desc(),
                self.model.id.desc(),
            )
        )

        stmt = self._with_relations(stmt)
        
        return await self._paginator.paginate_by_score(
            stmt=stmt,
            cursor=pagination.encoded_cursor if pagination else None,
        )

    async def get_by_slug(self, book_slug: str) -> Optional[BookModel]:
        stmt = self._base_query().where(self.model.slug == book_slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_list_by_category_slug(
        self,
        category_slug: str,
        random_pagination: CursorMD5RandomPaginationREQT,
    ) -> CursorPaginationDTO:
        stmt = (
            select(self.model)
            .join(BookCategoryModel, self.model.category_id == BookCategoryModel.id)
            .options(
                contains_eager(self.model.category),
                joinedload(self.model.author),
                joinedload(self.model.paper_type),
                joinedload(self.model.made_in),
            )
            .where(BookCategoryModel.slug == category_slug)
        )

        return await self._paginator.random_paginate(
            stmt=stmt,
            cursor=random_pagination.md5_cursor,
            seed=random_pagination.seed,
        )
    
    async def get_similar_list_by_category_and_author_id(
        self,
        similar: FilterSimilarBooksREQT,
        random_pagination: CursorMD5RandomPaginationREQT,
    ) -> CursorPaginationDTO:
        stmt = (
            self._base_query()
            .where(self.model.slug != similar.book_slug)
            .where(
                (self.model.author_id == similar.author_id) |
                (self.model.category_id == similar.category_id)
            )
        )

        return await self._paginator.random_paginate(
            stmt, 
            random_pagination.seed,
            random_pagination.md5_cursor,
        )
    
    async def get_list_by_ids(self, book_ids: List[int]) -> List[BookModel]:
        if not book_ids:
            return []

        stmt = self._base_query().where(self.model.id.in_(book_ids))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_list_by_ids_for_update(
        self,
        book_ids: List[int],
    ) -> List[BookModel]:
        """
        Блокирует строки книг (SELECT ... FOR UPDATE NOWAIT)
        для безопасного резервирования количества при покупке.

        ORDER BY id — обязателен: все транзакции берут блокировки
        в одном порядке, что исключает deadlock между заказами
        с пересекающимися наборами книг ({1,5} vs {5,1}).
        """
        if not book_ids:
            return []

        stmt = (
            select(self.model)
            .where(self.model.id.in_(book_ids))
            .order_by(self.model.id)
            .with_for_update(nowait=True)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_list_by_wishlist_user_id(self, user_id: int) -> List[BookModel]:
        result = await self.session.execute(
            select(BookModel)
            .join(WishlistModel, WishlistModel.book_id == BookModel.id)
            .where(WishlistModel.user_id == user_id)
        )

        return result.scalars().all()

    async def is_in_wishlist(self, user_id: int, book_id: int) -> bool:
        result = await self.session.execute(
            select(WishlistModel.book_id).where(
                WishlistModel.user_id == user_id,
                WishlistModel.book_id == book_id,
            )
        )
        return result.first() is not None

    async def remove_from_wishlist(self, user_id: int, book_id: int) -> None:
        await self.session.execute(
            delete(WishlistModel).where(
                WishlistModel.user_id == user_id,
                WishlistModel.book_id == book_id,
            )
        )

    async def get_category_and_author_id_by_book_id(
        self,
        book_id: int,
    ) -> tuple[int | None, int | None] | None:
        book = await self.session.execute(
            select(
                self.model.category_id,
                self.model.author_id,
            ).where(
                self.model.id == book_id
            )
        )

        return book.first()
    
    async def get_descriptions_by_ids(
        self,
        book_ids: list[int],
        limit: int = 5,
    ) -> list[str]:
        if not book_ids:
            return []

        books_desc = await self.session.execute(
            select(self.model.description)
            .where(
                self.model.id.in_(book_ids),
                self.model.description.isnot(None),
            )
            .limit(limit)
        )

        return books_desc.scalars().all()
    
    async def get_books_for_indexing(self) -> list[BooksQdrantPayloadDTO]:
        stmt = (
            select(BookModel)
            .options(
                joinedload(BookModel.author),
                joinedload(BookModel.category),
            )
            .where(BookModel.is_available.is_(True))
        )

        result = await self.session.execute(stmt)
        books = result.scalars().all()

        return [self._to_qdrant_payload_dto(book) for book in books]

    @staticmethod
    def _to_qdrant_payload_dto(book: BookModel) -> BooksQdrantPayloadDTO:
        return BooksQdrantPayloadDTO(
            id=book.id,
            title=book.title,
            description=book.description,
            author_id=book.author_id,
            author_name=book.author.name,
            category_id=book.category_id,
            category_name=book.category.title,
            issue_year=book.issue_year,
            rating=float(book.rating),
            is_available=book.is_available,
        )

    @staticmethod
    def _to_elastic_document_dto(book: BookModel) -> BookElasticDocumentDTO:
        return BookElasticDocumentDTO(
            id=book.id,
            title=book.title,
            author_id=book.author_id,
            author_name=book.author.name,
            category_id=book.category_id,
            category_slug=book.category.slug,
            category_name=book.category.title,
            country=book.made_in.country if book.made_in else None,
            issue_year=book.issue_year,
            rating=float(book.rating),
            is_available=book.is_available,
        )

    async def get_book_for_sync(
        self,
        book_id: int,
    ) -> tuple[BooksQdrantPayloadDTO, BookElasticDocumentDTO] | None:
        """Одна книга для событийной синхронизации Qdrant/ES. None — удалена."""
        stmt = (
            select(BookModel)
            .options(
                joinedload(BookModel.author),
                joinedload(BookModel.category),
                joinedload(BookModel.made_in),
            )
            .where(BookModel.id == book_id)
        )

        result = await self.session.execute(stmt)
        book = result.scalar_one_or_none()

        if book is None:
            return None

        return (
            self._to_qdrant_payload_dto(book),
            self._to_elastic_document_dto(book),
        )

    async def get_books_for_elastic_indexing(self) -> list[BookElasticDocumentDTO]:
        """
        Все книги (включая недоступные — фильтрация по is_available
        происходит на стороне поискового запроса в Elasticsearch).
        """
        stmt = (
            select(BookModel)
            .options(
                joinedload(BookModel.author),
                joinedload(BookModel.category),
                joinedload(BookModel.made_in),
            )
        )

        result = await self.session.execute(stmt)
        books = result.scalars().all()

        return [self._to_elastic_document_dto(book) for book in books]

    async def get_top_by_category(
        self,
        category_id: int,
        exclude_book_ids: list[int] | None = None,
        limit: int = 20,
    ):
        exclude_book_ids = exclude_book_ids or []

        stmt = (
            select(
                self.model.id,
                self.model.rating,
            )
            .where(
                self.model.category_id == category_id,
                self.model.is_available.is_(True),
            )
            .order_by(
                self.model.rating.desc(),
                self.model.total_sales.desc(),
            ).limit(limit)
        )

        if exclude_book_ids:
            stmt = stmt.where(
                self.model.id.notin_(exclude_book_ids)
            )

        result = await self.session.execute(stmt)
        return result.all()
    
    async def get_top_popular_books(
        self,
        limit: int,
        exclude_book_ids: list[int] | None = None,
    ):
        stmt = (
            select(
                self.model.id,
                self.model.rating,
            )
            .where(
                self.model.is_available.is_(True),
            )
            .order_by(
                self.model.total_sales.desc(),
                self.model.rating.desc(),
            ).limit(limit)
        )

        if exclude_book_ids:
            stmt = stmt.where(
                self.model.id.notin_(exclude_book_ids)
            )

        result = await self.session.execute(stmt)
        return result.all()
    
    async def get_preview_by_ids(
        self,
        book_ids: list[int],
    ) -> list[BookModel]:
        result = await self.session.execute(
            select(BookModel).where(
                BookModel.id.in_(book_ids)
            ).options(
                selectinload(BookModel.author),
                selectinload(BookModel.category),
            )
        )

        return result.scalars().all()