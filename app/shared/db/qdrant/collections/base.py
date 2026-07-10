from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    OptimizersConfigDiff,
    PayloadSchemaType,
    VectorParams,
)

class BaseQdrantCollection:
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        collection_name: str,
    ):
        self.client = qdrant_client
        self.collection_name = collection_name

    @property
    def vector_size(self) -> int:
        """Размер вектора коллекции. Наследники обязаны переопределить."""
        raise NotImplementedError(
            f"{type(self).__name__} must define vector_size"
        )

    @property
    def distance(self) -> Distance:
        return Distance.COSINE

    @property
    def payload_indexes(self) -> dict[str, PayloadSchemaType]:
        """
        Декларация payload-индексов: {имя_поля: тип}.
        По аналогии с index_mappings у BaseElasticIndex.
        """
        return {}

    async def init_collection(self) -> None:
        """Идемпотентная инициализация: коллекция + payload-индексы."""
        if not await self.collection_exists():
            await self.create_collection(
                vector_size=self.vector_size,
                distance=self.distance,
            )

        await self.create_payload_indexes()

    async def create_payload_indexes(self) -> None:
        """Создаёт недостающие payload-индексы из payload_indexes."""
        if not self.payload_indexes:
            return

        info = await self.get_info()
        existing_fields = set((info.payload_schema or {}).keys())

        for field_name, field_schema in self.payload_indexes.items():
            if field_name not in existing_fields:
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema,
                )

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