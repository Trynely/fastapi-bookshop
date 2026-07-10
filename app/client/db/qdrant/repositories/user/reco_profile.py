from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import HasIdCondition, Filter
from app.shared.db.qdrant.base_repository import BaseQdrantREPO

USER_RECO_PROFILE_COLLECTION = "user_reco_profile"

@dataclass(slots=True)
class UserQdrantSimilarDTO:
    user_id: int
    score: float

    top_categories: list[int]
    top_authors: list[int]


class UserRecoProfileQdrantREPO(BaseQdrantREPO):
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
    ):
        super().__init__(
            qdrant_client=qdrant_client,
            collection_name=USER_RECO_PROFILE_COLLECTION,
        )

    async def find_similar_users(
        self,
        vector: list[float],
        limit: int = 50,
        exclude_id: int | None = None,
    ) -> list[UserQdrantSimilarDTO]:
        query_filter = (
            Filter(
                must_not=[
                    HasIdCondition(
                        has_id=[exclude_id]
                    )
                ]
            )
            if exclude_id is not None
            else None
        )

        results = await self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

        return [
            UserQdrantSimilarDTO(
                user_id=int(point.id),
                score=float(point.score),
                top_categories=(
                    point.payload.get("top_categories", [])
                    if point.payload
                    else []
                ),
                top_authors=(
                    point.payload.get("top_authors", [])
                    if point.payload
                    else []
                ),
            )
            for point in results.points
        ]