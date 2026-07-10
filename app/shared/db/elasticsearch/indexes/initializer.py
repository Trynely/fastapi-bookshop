from typing import Sequence

from app.shared.db.elasticsearch.indexes.base import BaseElasticIndex


class ElasticIndexInitializer:
    def __init__(
        self,
        indexes: Sequence[BaseElasticIndex],
    ):
        self._indexes = indexes

    async def init(self) -> None:
        for index in self._indexes:
            await index.init_index()
