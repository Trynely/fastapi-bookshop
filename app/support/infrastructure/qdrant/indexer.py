"""
Индексатор базы знаний поддержки (FAQ -> Qdrant).

Схема коллекции создаётся автоматически при старте приложения
(QdrantCollectionInitializer) или командой `python -m app.cli init-db`.
Этот скрипт нужен только для (пере)заливки данных FAQ:

    python -m app.support.infrastructure.qdrant.indexer
"""

import asyncio

from app.core.container import create_dishka_container
from app.support.db.qdrant.collections.faq import FaqQdrantCollection


async def main() -> None:
    container = create_dishka_container()
    print("🚀 Запуск индексатора базы знаний...")

    try:
        async with container() as request_container:
            faq_collection = await request_container.get(FaqQdrantCollection)

            await faq_collection.init_collection()
            indexed = await faq_collection.make_index()

            print(f"🎉 Проиндексировано {indexed} записей FAQ. RAG готов к работе.")
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
