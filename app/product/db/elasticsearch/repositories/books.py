import base64
import json
from dataclasses import asdict
from typing import Optional

from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk

from app.core.config.base import get_settings
from app.core.config.product.book.elasticsearch_index_names import BOOKS_INDEX
from app.product.dto.book.elastic_document import BookElasticDocumentDTO
from app.shared.dto.cursor_pagination import CursorPaginationDTO

settings = get_settings()

# Поля документа, по которым разрешён полнотекстовый поиск
TITLE_FIELD = "title"
AUTHOR_NAME_FIELD = "author_name"
COUNTRY_FIELD = "country"


class BooksElasticREPO:
    def __init__(self, es_client: AsyncElasticsearch):
        self.es_client = es_client
        self.index_name = BOOKS_INDEX
        self.limit = settings.db.limit

    # -------
    # indexing

    async def index_batch(
        self,
        documents: list[BookElasticDocumentDTO],
    ) -> None:
        if not documents:
            return

        actions = [
            {
                "_op_type": "index",
                "_index": self.index_name,
                "_id": document.id,
                "book_id": document.id,
                **{
                    key: value
                    for key, value in asdict(document).items()
                    if key != "id"
                },
            }
            for document in documents
        ]

        await async_bulk(
            client=self.es_client,
            actions=actions,
        )

    async def delete_missing(self, actual_book_ids: list[int]) -> None:
        """
        Удаляет из индекса документы, которых больше нет в Postgres.
        Вызывается после полной переиндексации.
        """
        if not actual_book_ids:
            return

        await self.es_client.delete_by_query(
            index=self.index_name,
            query={
                "bool": {
                    "must_not": [
                        {"terms": {"book_id": actual_book_ids}},
                    ],
                },
            },
            conflicts="proceed",
        )

    # -------
    # search

    async def search_ids_in_category(
        self,
        category_slug: str,
        field: str,
        query: str,
        encoded_cursor: Optional[str] = None,
    ) -> CursorPaginationDTO:
        """
        Полнотекстовый поиск книг внутри категории.
        Сортировка по релевантности (_score), пагинация — search_after,
        курсор — непрозрачная base64-строка.

        Возвращает CursorPaginationDTO, где items — id книг
        в порядке релевантности.
        """
        search_body: dict = {
            "index": self.index_name,
            "size": self.limit + 1,
            "source_includes": ["book_id"],
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"category_slug": category_slug}},
                        {"term": {"is_available": True}},
                    ],
                    "must": [
                        {
                            "bool": {
                                "should": [
                                    # Точное совпадение слов (с опечатками) — выше
                                    {
                                        "match": {
                                            field: {
                                                "query": query,
                                                "operator": "and",
                                                "fuzziness": "AUTO",
                                                "boost": 2.0,
                                            },
                                        },
                                    },
                                    # Префиксное совпадение (edge_ngram)
                                    {
                                        "match": {
                                            f"{field}.prefix": {
                                                "query": query,
                                                "operator": "and",
                                            },
                                        },
                                    },
                                ],
                                "minimum_should_match": 1,
                            },
                        },
                    ],
                },
            },
            # tie-breaker по book_id — стабильный порядок при равном score
            "sort": [
                {"_score": {"order": "desc"}},
                {"book_id": {"order": "desc"}},
            ],
        }

        if encoded_cursor:
            search_body["search_after"] = self._decode_cursor(encoded_cursor)

        response = await self.es_client.search(**search_body)
        hits = response["hits"]["hits"]

        has_more = len(hits) > self.limit
        hits = hits[: self.limit]

        next_cursor = (
            self._encode_cursor(hits[-1]["sort"]) if has_more else None
        )

        return CursorPaginationDTO(
            items=[hit["_source"]["book_id"] for hit in hits],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    # -------
    # cursor

    @staticmethod
    def _encode_cursor(sort_values: list) -> str:
        return base64.b64encode(
            json.dumps(sort_values).encode()
        ).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> list:
        """
        Бросает ValueError при невалидном курсоре —
        обработчик выше должен вернуть HTTP 400.
        """
        try:
            decoded = json.loads(base64.b64decode(cursor).decode())

            if (
                not isinstance(decoded, list)
                or len(decoded) != 2
            ):
                raise ValueError

            score, book_id = float(decoded[0]), int(decoded[1])
            return [score, book_id]
        except (ValueError, TypeError, json.JSONDecodeError):
            raise ValueError("Невалидный курсор пагинации")
