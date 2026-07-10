from qdrant_client import AsyncQdrantClient
from itertools import islice
from app.core.config.product.book.qdrant_collection_names import BOOKS_COLLECTION
from app.core.config.shared.qdrant.embedding import VECTOR_SIZE
from app.product.db.qdrant.repositories.books import BooksQdrantREPO
from app.product.dto.book.qdrant_payload import BooksQdrantPayloadDTO
from app.shared.db.qdrant.collections.base import BaseQdrantCollection
from app.shared.dto.qdrant_point import QdrantPointDTO
from app.shared.service.infrastructure.ollama.embedder import OllamaEmbedder

EMBED_BATCH_SIZE = 100

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

    @staticmethod
    def _chunked(items, size: int):
        iterator = iter(items)

        while chunk := list(islice(iterator, size)):
            yield chunk

    async def init_collection(self):
        if not await self.collection_exists():
            await self.create_collection(
                VECTOR_SIZE,
            )

    async def make_index(
        self,
        books: list[BooksQdrantPayloadDTO],
    ) -> None:
        if not books:
            return

        for books_batch in self._chunked(
            items=books,
            size=EMBED_BATCH_SIZE,
        ):
            texts = [
                self.book_text_embedding.execute(book)
                for book in books_batch
            ]

            vectors = await self._embedder.embed_batch(texts)

            points = [
                QdrantPointDTO(
                    id=book.id,
                    vector=vector,
                    payload={
                        "book_id": book.id,
                        "title": book.title,
                        "author_id": book.author_id,
                        "author_name": book.author_name,
                        "category_id": book.category_id,
                        "category_name": book.category_name,
                        "rating": book.rating,
                        "issue_year": book.issue_year,
                        "is_available": book.is_available,
                    },
                )
                for book, vector in zip(
                    books_batch,
                    vectors,
                    strict=True,
                )
            ]

            await self.books_qdrant_point_repo.save_batch(points=points)