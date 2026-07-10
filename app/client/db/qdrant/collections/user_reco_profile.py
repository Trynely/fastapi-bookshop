from qdrant_client import AsyncQdrantClient
from app.client.db.qdrant.repositories.user.reco_profile import USER_RECO_PROFILE_COLLECTION
from app.core.config.shared.qdrant.embedding import VECTOR_SIZE
from app.shared.db.qdrant.collections.base import BaseQdrantCollection

class UserRecoProfileQdrantCollection(BaseQdrantCollection):
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
    ):
        super().__init__(
            qdrant_client=qdrant_client,
            collection_name=USER_RECO_PROFILE_COLLECTION,
        )

    async def init_collection(self):
        if not await self.collection_exists():
            await self.create_collection(
                VECTOR_SIZE,
            )