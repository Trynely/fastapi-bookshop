from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Any, Filter, PointIdsList, PointStruct, ScoredPoint
from app.shared.dto.qdrant_point import QdrantPointDTO

class BaseQdrantREPO:
    def __init__(
        self, 
        qdrant_client: AsyncQdrantClient, 
        collection_name: str
    ):
        self.client = qdrant_client
        self.collection_name = collection_name

    async def save_batch(
        self,
        points: list[QdrantPointDTO],
        wait: bool = True,
        timeout: int | None = None,
    ) -> None:
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point.id,
                    vector=point.vector,
                    payload=point.payload,
                )
                for point in points
            ],
            wait=wait,
            timeout=timeout,
        )

    async def save(
        self,
        point: QdrantPointDTO,
        wait: bool = True,
        timeout: int | None = None,
    ) -> None:
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point.id,
                    vector=point.vector,
                    payload=point.payload,
                )
            ],
            wait=wait,
            timeout=timeout,
        )

    async def remove_all(
        self,
        point_ids: list[int],
        wait=True,
        timeout: int | None = None,
    ) -> None:
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(
                points=point_ids,
            ),
            wait=wait,
            timeout=timeout,
        )

    async def remove(
        self,
        point_id: int,
        wait=True,
        timeout: int | None = None,
    ) -> None:
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=PointIdsList(
                points=[point_id],
            ),
            wait=wait,
            timeout=timeout,
        )

    async def get(
        self,
        point_ids: list[int],
        with_payload=True,
        with_vectors=False,
    ):
        return await self.client.retrieve(
            collection_name=self.collection_name,
            ids=point_ids,
            with_payload=with_payload,
            with_vectors=with_vectors,
        )

    async def search(
        self,
        query_vector: list[float],
        limit: int = 10,
        query_filter: Filter | None = None,
    ) -> list[ScoredPoint]:
        return await self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )

    async def scroll(
        self,
        limit: int = 10,
        query_filter: Filter | None = None,
        with_payload=True,
        with_vectors=False,
        offset: int = 0,
        timeout: int | None = None,
    ):
        return await self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=query_filter,
            limit=limit,
            with_payload=with_payload,
            with_vectors=with_vectors,
            offset=offset,
            timeout=timeout,
        )

    async def count(
        self,
        query_filter: Filter | None = None,
        exact=True,
        timeout: int | None = None,
    ) -> int:
        result = await self.client.count(
            collection_name=self.collection_name,
            count_filter=query_filter,
            exact=exact,
            timeout=timeout,
        )
        return result.count
    
    async def get_similar(
        self,
        query: Any,
        limit: int = 10,
        query_filter: Filter | None = None,
        with_payload: bool = True,
        with_vectors: bool = False,
        score_threshold: float | None = None,
        timeout: int | None = None,
    ):
        result = await self.client.query_points(
            collection_name=self.collection_name,
            query=query,
            query_filter=query_filter,
            limit=limit,
            with_payload=with_payload,
            with_vectors=with_vectors,
            score_threshold=score_threshold,
            timeout=timeout,
        )

        return result.points

    async def get_context(
        self,
        query_vector: str,
        limit: int = 5,
        score_threshold: float = 0.5
    ) -> str:
        try:
            result = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
                score_threshold=score_threshold
            )

            if not result.points:
                return ""

            contexts = [
                hit.payload.get("text", "") 
                for hit in result.points 
                if hit.payload and "text" in hit.payload
            ]

            return "\n---\n".join(contexts)
        except Exception as e:
            print(f"Qdrant Search Error: {e}")
            return ""