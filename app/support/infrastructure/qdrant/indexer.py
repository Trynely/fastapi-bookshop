import asyncio
import uuid
from dishka import make_async_container
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models
from app.core.config.shared.qdrant.collections import QDRANT_COLLECTION_NAME
from app.core.config.shared.qdrant.embedding import VECTOR_SIZE
from app.shared.container import QdrantProvider
from app.core.config.support.llm.faq import FAQ_DATA
from app.support.infrastructure.qdrant.embedding import get_embedding

async def init_qdrant_and_index_data(qdrant_client: AsyncQdrantClient):
    collections_response = await qdrant_client.get_collections()
    collection_names = [col.name for col in collections_response.collections]

    if QDRANT_COLLECTION_NAME not in collection_names:
        print(f"📦 Создаем новую коллекцию '{QDRANT_COLLECTION_NAME}'...")

        await qdrant_client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE
            )
        )
    else:
        print(f"✅ Коллекция '{QDRANT_COLLECTION_NAME}' уже существует. Добавляем данные...")

    points = []
    print("🧠 Генерируем векторы для FAQ...")
    
    for item in FAQ_DATA:
        text_to_embed = item["question"] + " " + item["answer"]
        embedding = await get_embedding(text_to_embed)

        if embedding:
            point_id = str(uuid.uuid4())
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "question": item["question"],
                        "answer": item["answer"],
                        "text": text_to_embed
                    }
                )
            )

    if points:
        print("💾 Загружаем векторы в Qdrant...")
        await qdrant_client.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=points
        )
        print("🎉 Индексация успешно завершена! RAG готов к работе.")
    else:
        print("⚠️ Не удалось получить эмбеддинги. Данные не загружены.")

async def main():
    container = make_async_container(QdrantProvider())
    print("🚀 Запуск индексатора базы знаний...")
    
    async with container() as request_container:
        client = await request_container.get(AsyncQdrantClient)
        await init_qdrant_and_index_data(client)
    
    await container.close()

if __name__ == "__main__":
    asyncio.run(main())