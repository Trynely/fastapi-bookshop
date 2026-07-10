import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from app.core.config.shared.qdrant.collections import QDRANT_COLLECTION_NAME
from app.core.config.shared.qdrant.embedding import VECTOR_SIZE
from app.core.config.support.llm.faq import FAQ_DATA
from app.shared.db.qdrant.collections.base import BaseQdrantCollection
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder

# детерминированные id: повторный прогон обновляет точки, а не дублирует их
_FAQ_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "bookshop.support.faq")


class FaqQdrantCollection(BaseQdrantCollection):
    """Коллекция базы знаний поддержки (RAG по FAQ)."""

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        embedder: OllamaEmbedder,
    ):
        super().__init__(
            qdrant_client=qdrant_client,
            collection_name=QDRANT_COLLECTION_NAME,
        )
        self._embedder = embedder

    @property
    def vector_size(self) -> int:
        return VECTOR_SIZE

    # payload-индексы не нужны: поиск чисто векторный, без фильтров

    async def make_index(
        self,
        faq_items: list[dict] | None = None,
    ) -> int:
        """Эмбеддит FAQ и загружает в коллекцию. Идемпотентно."""
        items = faq_items if faq_items is not None else FAQ_DATA

        if not items:
            return 0

        texts = [
            f'{item["question"]} {item["answer"]}'
            for item in items
        ]

        vectors = await self._embedder.embed_batch(texts)

        points = [
            PointStruct(
                id=str(uuid.uuid5(_FAQ_NAMESPACE, item["question"])),
                vector=vector,
                payload={
                    "question": item["question"],
                    "answer": item["answer"],
                    "text": text,
                },
            )
            for item, text, vector in zip(items, texts, vectors, strict=True)
        ]

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

        return len(points)
