"""
CLI для инициализации хранилищ.

    python -m app.cli init-db       # всё сразу: Postgres + Qdrant + Elasticsearch
    python -m app.cli migrate       # только alembic upgrade head
    python -m app.cli init-search   # только Qdrant-коллекции + ES-индексы

Все команды идемпотентны — можно запускать на каждый деплой
(entrypoint контейнера, шаг CI/CD и т.п.).
"""

import argparse
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def migrate() -> None:
    """Postgres: alembic upgrade head."""
    from alembic import command
    from alembic.config import Config

    print("⏫ Postgres: alembic upgrade head...")

    alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location",
        str(PROJECT_ROOT / "alembic"),
    )

    # env.py сам запускает asyncio.run -> вызываем строго из sync-контекста
    command.upgrade(alembic_cfg, "head")

    print("✅ Postgres: миграции применены.")


async def _init_search_stores() -> None:
    from app.core.container import create_dishka_container
    from app.shared.db.elasticsearch.indexes.initializer import ElasticIndexInitializer
    from app.shared.db.qdrant.collections.intializer import QdrantCollectionInitializer

    container = create_dishka_container()

    try:
        async with container() as request_container:
            print("⏫ Qdrant: инициализация коллекций и payload-индексов...")
            qdrant_initializer = await request_container.get(
                QdrantCollectionInitializer,
            )
            await qdrant_initializer.init()
            print("✅ Qdrant: готово.")

            print("⏫ Elasticsearch: инициализация индексов...")
            elastic_initializer = await request_container.get(
                ElasticIndexInitializer,
            )
            await elastic_initializer.init()
            print("✅ Elasticsearch: готово.")
    finally:
        await container.close()


def init_search() -> None:
    """Qdrant + Elasticsearch."""
    asyncio.run(_init_search_stores())


def init_db() -> None:
    """Полная инициализация всех хранилищ."""
    migrate()
    init_search()
    print("🎉 Все хранилища инициализированы.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Инициализация хранилищ (Postgres, Qdrant, Elasticsearch).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="миграции + Qdrant + Elasticsearch")
    subparsers.add_parser("migrate", help="только alembic upgrade head")
    subparsers.add_parser("init-search", help="только Qdrant + Elasticsearch")

    args = parser.parse_args()

    handlers = {
        "init-db": init_db,
        "migrate": migrate,
        "init-search": init_search,
    }
    handlers[args.command]()


if __name__ == "__main__":
    main()
