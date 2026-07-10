from elasticsearch import AsyncElasticsearch


class BaseElasticIndex:
    """
    Базовый класс индекса Elasticsearch.
    Наследники описывают settings/mappings — по аналогии с BaseQdrantCollection.
    """

    def __init__(
        self,
        es_client: AsyncElasticsearch,
        index_name: str,
    ):
        self.es_client = es_client
        self.index_name = index_name

    @property
    def index_settings(self) -> dict:
        return {}

    @property
    def index_mappings(self) -> dict:
        return {}

    async def index_exists(self) -> bool:
        return bool(
            await self.es_client.indices.exists(index=self.index_name)
        )

    async def init_index(self) -> None:
        if not await self.index_exists():
            await self.es_client.indices.create(
                index=self.index_name,
                settings=self.index_settings,
                mappings=self.index_mappings,
            )
