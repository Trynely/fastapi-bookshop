from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, OptimizersConfigDiff, VectorParams

class BaseQdrantCollection:
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        collection_name: str,
    ):
        self.client = qdrant_client
        self.collection_name = collection_name

    async def collection_exists(self) -> bool:
        return await self.client.collection_exists(
            collection_name=self.collection_name,
        )

    async def create_collection(
        self,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ) -> None:
        await self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance,
            ),
        )

    async def recreate(
        self,
        vector_size: int,
        distance: Distance = Distance.COSINE,
    ) -> None:
        if await self.collection_exists():
            await self.delete()

        await self.create_collection(
            vector_size=vector_size,
            distance=distance,
        )

    async def delete(self) -> None:
        await self.client.delete_collection(
            collection_name=self.collection_name,
        )

    async def get_info(self):
        return await self.client.get_collection(
            collection_name=self.collection_name,
        )

    async def list(self):
        collections = await self.client.get_collections()
        return collections.collections

    async def update_optimizer(
        self,
        indexing_threshold: int = 10000,
    ) -> None:
        await self.client.update_collection(
            collection_name=self.collection_name,
            optimizer_config=OptimizersConfigDiff(
                indexing_threshold=indexing_threshold,
            ),
        )

    async def count_points(self) -> int:
        result = await self.client.count(
            collection_name=self.collection_name,
            exact=True,
        )
        return result.count

    async def clear(self) -> None:
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector={
                "filter": {}
            },
        )