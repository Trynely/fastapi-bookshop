import hashlib
import json
from itertools import islice

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PayloadSchemaType, PointIdsList

from app.core.config.product.book.qdrant_collection_names import BOOKS_COLLECTION
from app.core.config.shared.qdrant.embedding import VECTOR_SIZE
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.product.dto.book.qdrant_payload import BooksQdrantPayloadDTO
from app.shared.db.qdrant.collections.base import BaseQdrantCollection
from app.shared.dto.qdrant_point import QdrantPointDTO
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder

EMBED_BATCH_SIZE = 100
SCROLL_BATCH_SIZE = 1000

# служебные поля payload для реконсиляции
EMBED_HASH_FIELD = "embed_hash"
META_HASH_FIELD = "meta_hash"


def _md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


class BooksEmbeddingTextBuilder:
    @staticmethod
    def execute(
        book: BooksQdrantPayloadDTO,
    ) -> str:
        parts = [
            f"Title: {book.title}",
            f"Author: {book.author_name}",
            f"Category: {book.category_name}",
        ]

        if book.issue_year:
            parts.append(
                f"Released: {book.issue_year}"
            )

        if book.description:
            parts.append(
                book.description[:1000]
            )

        return ". ".join(parts)


class BooksQdrantCollection(BaseQdrantCollection):
    def __init__(
        self,
        embedder: OllamaEmbedder,
        books_qdrant_point_repo: BooksQdrantREPO,
        qdrant_client: AsyncQdrantClient,
        book_text_embedding: BooksEmbeddingTextBuilder,
    ):
        super().__init__(
            qdrant_client=qdrant_client,
            collection_name=BOOKS_COLLECTION,
        )
        self.books_qdrant_point_repo = books_qdrant_point_repo
        self._embedder = embedder
        self.book_text_embedding = book_text_embedding

    @property
    def vector_size(self) -> int:
        return VECTOR_SIZE

    @property
    def payload_indexes(self) -> dict[str, PayloadSchemaType]:
        # поля, по которым фильтруются запросы
        # (recommendations_for_user_profile, agents/tools/books.py)
        return {
            "category_id": PayloadSchemaType.INTEGER,
            "author_id": PayloadSchemaType.INTEGER,
            "is_available": PayloadSchemaType.BOOL,
        }

    @staticmethod
    def _chunked(items, size: int):
        iterator = iter(items)

        while chunk := list(islice(iterator, size)):
            yield chunk

    # -------
    # payload / hashes

    @staticmethod
    def _core_payload(book: BooksQdrantPayloadDTO) -> dict:
        return {
            "book_id": book.id,
            "title": book.title,
            "author_id": book.author_id,
            "author_name": book.author_name,
            "category_id": book.category_id,
            "category_name": book.category_name,
            "rating": book.rating,
            "issue_year": book.issue_year,
            "is_available": book.is_available,
        }

    def _build_payload(
        self,
        book: BooksQdrantPayloadDTO,
        embed_hash: str,
    ) -> dict:
        core = self._core_payload(book)

        return {
            **core,
            EMBED_HASH_FIELD: embed_hash,
            META_HASH_FIELD: _md5(json.dumps(core, sort_keys=True)),
        }

    # -------
    # indexing

    async def _embed_and_upsert(
        self,
        books_with_text: list[tuple[BooksQdrantPayloadDTO, str]],
    ) -> None:
        """Эмбеддит и заливает (book, embed_text) батчами."""
        for batch in self._chunked(books_with_text, EMBED_BATCH_SIZE):
            texts = [text for _, text in batch]
            vectors = await self._embedder.embed_batch(texts)

            points = [
                QdrantPointDTO(
                    id=book.id,
                    vector=vector,
                    payload=self._build_payload(book, _md5(text)),
                )
                for (book, text), vector in zip(batch, vectors, strict=True)
            ]

            await self.books_qdrant_point_repo.save_batch(points=points)

    async def make_index(
        self,
        books: list[BooksQdrantPayloadDTO],
    ) -> None:
        """Безусловный upsert (используется событийной синхронизацией)."""
        if not books:
            return

        await self._embed_and_upsert([
            (book, self.book_text_embedding.execute(book))
            for book in books
        ])

    # -------
    # reconciliation

    async def _existing_hashes(self) -> dict[int, tuple[str | None, str | None]]:
        """{point_id: (embed_hash, meta_hash)} для всех точек коллекции."""
        result: dict[int, tuple[str | None, str | None]] = {}
        offset = None

        while True:
            points, offset = await self.client.scroll(
                collection_name=self.collection_name,
                limit=SCROLL_BATCH_SIZE,
                offset=offset,
                with_payload=[EMBED_HASH_FIELD, META_HASH_FIELD],
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}
                result[int(point.id)] = (
                    payload.get(EMBED_HASH_FIELD),
                    payload.get(META_HASH_FIELD),
                )

            if offset is None:
                break

        return result

    async def reconcile(
        self,
        books: list[BooksQdrantPayloadDTO],
    ) -> dict[str, int]:
        """
        Приводит коллекцию к состоянию Postgres:
        - новый / изменённый текст  -> пересчёт эмбеддинга + upsert
        - изменилась только мета    -> overwrite_payload (без Ollama)
        - точки без книги в выборке -> удаление (книга удалена/недоступна)

        Идемпотентно и дёшево: неизменившиеся книги не трогаются вовсе.
        """
        existing = await self._existing_hashes()

        actual_ids: set[int] = set()
        to_embed: list[tuple[BooksQdrantPayloadDTO, str]] = []
        meta_updates: list[tuple[int, dict]] = []

        for book in books:
            actual_ids.add(book.id)

            text = self.book_text_embedding.execute(book)
            embed_hash = _md5(text)
            payload = self._build_payload(book, embed_hash)

            old = existing.get(book.id)

            if old is None or old[0] != embed_hash:
                to_embed.append((book, text))
            elif old[1] != payload[META_HASH_FIELD]:
                meta_updates.append((book.id, payload))

        to_delete = [
            point_id for point_id in existing
            if point_id not in actual_ids
        ]

        await self._embed_and_upsert(to_embed)

        for point_id, payload in meta_updates:
            await self.client.overwrite_payload(
                collection_name=self.collection_name,
                payload=payload,
                points=[point_id],
            )

        if to_delete:
            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=to_delete),
            )

        return {
            "embedded": len(to_embed),
            "meta_updated": len(meta_updates),
            "deleted": len(to_delete),
            "unchanged": len(actual_ids) - len(to_embed) - len(meta_updates),
        }
