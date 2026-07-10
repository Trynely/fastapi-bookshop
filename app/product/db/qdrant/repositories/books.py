from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, HasIdCondition, MatchAny, MatchValue, ScoredPoint
from app.core.config.product.book.qdrant_collection_names import BOOKS_COLLECTION
from app.shared.db.qdrant.base_repository import BaseQdrantREPO

class BooksQdrantREPO(BaseQdrantREPO):
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
    ):
        super().__init__(
            qdrant_client=qdrant_client,
            collection_name=BOOKS_COLLECTION,
        )

    async def recommendations_for_user_profile(
        self,
        vector: list[float],
        limit: int = 20,
        exclude_ids: list[int] | None = None,
        category_ids: list[int] | None = None,
    ) -> list[ScoredPoint]:
        must = []
        must_not = []

        if exclude_ids:
            must_not.append(
                HasIdCondition(
                    has_id=exclude_ids
                )
            )

        if category_ids:
            must.append(
                FieldCondition(
                    key="category_id",
                    match=MatchAny(
                        any=category_ids
                    ),
                )
            )

        query_filter = (
            Filter(
                must=must,
                must_not=must_not,
            )
            if must or must_not
            else None
        )

        return await self.get_similar(
            query=vector,
            limit=limit,
            query_filter=query_filter,
        )