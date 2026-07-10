from elasticsearch import AsyncElasticsearch

from app.core.config.product.book.elasticsearch_index_names import BOOKS_INDEX
from app.shared.db.elasticsearch.indexes.base import BaseElasticIndex


class BooksElasticIndex(BaseElasticIndex):
    def __init__(self, es_client: AsyncElasticsearch):
        super().__init__(
            es_client=es_client,
            index_name=BOOKS_INDEX,
        )

    @property
    def index_settings(self) -> dict:
        return {
            "analysis": {
                "filter": {
                    "edge_ngram_filter": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 20,
                    },
                },
                "analyzer": {
                    # Базовый анализатор: работает и для русского, и для латиницы
                    "text_search": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"],
                    },
                    # Индексный анализатор для префиксного поиска
                    # (аналог поведения ILIKE 'подстрока%' + fuzzy сверху)
                    "text_prefix": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "asciifolding",
                            "edge_ngram_filter",
                        ],
                    },
                },
            },
        }

    @property
    def index_mappings(self) -> dict:
        searchable_text = {
            "type": "text",
            "analyzer": "text_search",
            "fields": {
                "prefix": {
                    "type": "text",
                    "analyzer": "text_prefix",
                    "search_analyzer": "text_search",
                },
            },
        }

        return {
            "properties": {
                "book_id": {"type": "long"},
                "title": searchable_text,
                "author_id": {"type": "long"},
                "author_name": searchable_text,
                "category_id": {"type": "long"},
                "category_slug": {"type": "keyword"},
                "category_name": {"type": "keyword"},
                "country": searchable_text,
                "issue_year": {"type": "integer"},
                "rating": {"type": "float"},
                "is_available": {"type": "boolean"},
            },
        }
