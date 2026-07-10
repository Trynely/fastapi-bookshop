from dishka import (
    Provider,
    provide,
    Scope,
)
from elasticsearch import AsyncElasticsearch
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.client.db.postgres.repositories.sqlalchemy import UserSQLAlchemyREPO
from app.client.db.postgres.repositories.sqlalchemy.user_event import UserEventSQLAlchemyREPO
from app.client.db.qdrant.repositories.user.reco_profile import UserRecoProfileQdrantREPO
from app.client.service.infrastructure.taskiq.schedules.user.base import UserTaskiqSchedulesPublisher
from app.client.service.infrastructure.user.reco_profile import UserPersonalBooksRecoProfile, UserPersonalBooksRecoProfileCache, UserProfileUpdateProcess
from app.core.db.postgres import DatabaseHelper
from app.product.db.postgres.repositories.sqlalchemy.author import BookAuthorSQLAlchemyREPO
from app.product.db.postgres.repositories.sqlalchemy.book import BookSQLAlchemyREPO
from app.product.db.postgres.repositories.sqlalchemy.category import BookCategorySQLAlchemyREPO
from app.product.db.postgres.repositories.sqlalchemy.review import BookReviewSQLAlchemyREPO
from app.product.db.elasticsearch.indexes.books import BooksElasticIndex
from app.product.db.elasticsearch.repositories.books import BooksElasticREPO
from app.product.db.qdrant.collections.books import BooksEmbeddingTextBuilder, BooksQdrantCollection
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.product.service.infrastructure.query_handlers import (
    CategoryBooksSearchQH,
    BookSimilarQH,
)
from app.product.service.infrastructure.query_handlers.book.detail import BookDetailQH
from app.product.service.infrastructure.query_handlers.book.filter import BookFilterQH
from app.product.service.infrastructure.query_handlers.book.main_reco import (
    BookColdCandidatesProvider,
    BookMainExplorationReco,
    BookMainNewReco,
    BookMainPopularReco,
    BookMainRecoBlender,
    BookMainRecoSeenSession,
    BookPersonalizedReco,
    BooksMainRecommendationsQH,
)
from app.product.service.infrastructure.query_handlers.review.filter import BookReviewFilterQH
from app.product.service.usecase.book.personal_reco import BookPersonalRecoForUserUC
from app.product.service.usecase.review.write import WriteReview
from app.shared.db.postgres.repositories.sqlalchemy.transaction import SQLAlchemyTransaction
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder
from app.shared.service.infrastructure.redis.clients import RedisClient

class BookProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def cold_candidates_provider(
        self,
        db_helper: DatabaseHelper,
        redis: RedisClient,
    ) -> BookColdCandidatesProvider:
        return BookColdCandidatesProvider(
            db_helper=db_helper,
            redis=redis,
        )

    @provide
    def personalized_feed_source(
        self,
        db_helper: DatabaseHelper,
        books_qdrant_repo: BooksQdrantREPO,
        user_reco_profile_qdrant_repo: UserRecoProfileQdrantREPO,
        cold_candidates: BookColdCandidatesProvider,
    ) -> BookPersonalizedReco:
        return BookPersonalizedReco(
            db_helper=db_helper,
            books_qdrant_repo=books_qdrant_repo,
            user_reco_profile_qdrant_repo=user_reco_profile_qdrant_repo,
            cold_candidates=cold_candidates,
        )

    @provide
    def popular_feed_source(
        self,
        db_helper: DatabaseHelper,
        cold_candidates: BookColdCandidatesProvider,
    ) -> BookMainPopularReco:
        return BookMainPopularReco(
            db_helper=db_helper,
            cold_candidates=cold_candidates,
        )

    @provide
    def new_books_feed_source(
        self,
        db_helper: DatabaseHelper,
    ) -> BookMainNewReco:
        return BookMainNewReco(db_helper=db_helper)

    @provide
    def exploration_feed_source(
        self,
        db_helper: DatabaseHelper,
    ) -> BookMainExplorationReco:
        return BookMainExplorationReco(db_helper=db_helper)

    @provide
    def blender_mixer(
        self,
    ) -> BookMainRecoBlender:
        return BookMainRecoBlender()
    
    @provide
    def feed_session_store(
        self,
        redis: RedisClient,
    ) -> BookMainRecoSeenSession:
        return BookMainRecoSeenSession(redis=redis)

    @provide
    def blender_feed_uc(
        self,
        user_reco_profile: UserPersonalBooksRecoProfile,
        personalized_source: BookPersonalizedReco,
        popular_source: BookMainPopularReco,
        new_books_source: BookMainNewReco,
        exploration_source: BookMainExplorationReco,
        mixer: BookMainRecoBlender,
        book_repository: BookSQLAlchemyREPO,
        feed_session_store: BookMainRecoSeenSession,
    ) -> BooksMainRecommendationsQH:
        return BooksMainRecommendationsQH(
            user_reco_profile=user_reco_profile,
            personalized=personalized_source,
            popular=popular_source,
            new=new_books_source,
            exploration=exploration_source,
            blender=mixer,
            book_repository=book_repository,
            book_reco_session=feed_session_store,
        )

    @provide
    def book_repository(
        self,
        session: AsyncSession,
    ) -> BookSQLAlchemyREPO:
        return BookSQLAlchemyREPO(session)
    
    @provide
    def book_filter_qh(
        self,
        book_repository: BookSQLAlchemyREPO,
    ) -> BookFilterQH:
        return BookFilterQH(book_repository=book_repository)
    
    @provide
    def book_detail_qh(
        self,
        book_repository: BookSQLAlchemyREPO,
    ) -> BookDetailQH:
        return BookDetailQH(book_repository=book_repository)
    
    @provide
    def search_category_books_qh(
        self,
        books_elastic_repo: BooksElasticREPO,
        book_repository: BookSQLAlchemyREPO,
    ) -> CategoryBooksSearchQH:
        return CategoryBooksSearchQH(
            books_elastic_repo=books_elastic_repo,
            book_repository=book_repository,
        )
    
    @provide
    def recommendation_books_qh(
        self,
        book_repository: BookSQLAlchemyREPO,
    ) -> BookSimilarQH:
        return BookSimilarQH(book_repository=book_repository)
    
    @provide
    def book_generator_personal_reco_uc(
        self,
        redis: RedisClient,
        user_profile_cache: UserPersonalBooksRecoProfileCache,
        transaction: SQLAlchemyTransaction,
        book_repository: BookSQLAlchemyREPO,
        user_event_repository: UserEventSQLAlchemyREPO,
        schedule_publisher: UserTaskiqSchedulesPublisher,
    ) -> BookPersonalRecoForUserUC:
        return BookPersonalRecoForUserUC(
            redis=redis,
            transaction=transaction,
            schedule_publisher=schedule_publisher,
            user_profile_cache=user_profile_cache,
            book_repository=book_repository,
            user_event_repository=user_event_repository,
        )
    

    # qdrant

    @provide(scope=Scope.APP)
    def books_qdrant_point_repo(
        self,
        qdrant_client: AsyncQdrantClient,
    ) -> BooksQdrantREPO:
        return BooksQdrantREPO(
            qdrant_client=qdrant_client,
        )

    @provide(scope=Scope.APP)
    def books_qdrant_collection(
        self,
        books_qdrant_point_repo: BooksQdrantREPO,
        embedder: OllamaEmbedder,
        qdrant_client: AsyncQdrantClient,
        book_text_embedder: BooksEmbeddingTextBuilder,
    ) -> BooksQdrantCollection:
        return BooksQdrantCollection(
            books_qdrant_point_repo=books_qdrant_point_repo,
            embedder=embedder,
            qdrant_client=qdrant_client,
            book_text_embedding=book_text_embedder,
        )
    
    @provide(scope=Scope.APP)
    def books_embedding_text_builder(self) -> BooksEmbeddingTextBuilder:
        return BooksEmbeddingTextBuilder()


    # elasticsearch

    @provide(scope=Scope.APP)
    def books_elastic_repo(
        self,
        es_client: AsyncElasticsearch,
    ) -> BooksElasticREPO:
        return BooksElasticREPO(
            es_client=es_client,
        )

    @provide(scope=Scope.APP)
    def books_elastic_index(
        self,
        es_client: AsyncElasticsearch,
    ) -> BooksElasticIndex:
        return BooksElasticIndex(
            es_client=es_client,
        )


class BookReviewProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def review_repository(
        self,
        session: AsyncSession,
    ) -> BookReviewSQLAlchemyREPO:
        return BookReviewSQLAlchemyREPO(session)
    
    @provide
    def book_review_filter_qh(
        self,
        review_repository: BookReviewSQLAlchemyREPO,
    ) -> BookReviewFilterQH:
        return BookReviewFilterQH(review_repository=review_repository)
    
    @provide
    def write_review_uc(
        self,
        transaction: SQLAlchemyTransaction,
        book_repository: BookSQLAlchemyREPO,
        user_repository: UserSQLAlchemyREPO,
        review_repository: BookReviewSQLAlchemyREPO,
    ) -> WriteReview:
        return WriteReview(
            book_repository=book_repository,
            user_repository=user_repository,
            review_repository=review_repository,
            transaction=transaction,
        )


class BookAuthorProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def author_repository(
        self,
        session: AsyncSession,
    ) -> BookAuthorSQLAlchemyREPO:
        return BookAuthorSQLAlchemyREPO(session)
    

class BookCategoryProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def category_repository(
        self,
        session: AsyncSession,
    ) -> BookCategorySQLAlchemyREPO:
        return BookCategorySQLAlchemyREPO(session)


product_providers = [
    BookProvider(), 
    BookReviewProvider(),
    BookAuthorProvider(),
    BookCategoryProvider(),
]