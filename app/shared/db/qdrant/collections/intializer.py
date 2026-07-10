from typing import Sequence
from app.shared.db.qdrant.collections.base import BaseQdrantCollection

class QdrantCollectionInitializer:
    def __init__(
        self,
        collections: Sequence[BaseQdrantCollection],
    ):
        self._collections = collections

    async def init(self) -> None:
        for collection in self._collections:
            await collection.init_collection()