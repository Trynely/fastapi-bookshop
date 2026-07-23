from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles
from app.admin.registry import ADMIN_VIEWS
from app.admin.setup import init_admin
from app.core.logging import setup_logging
from app.core.main_page import template_router
from app.core.config.base import get_settings
from app.core.db.postgres import db_helper as database
from app.core.db.redis import close_redis
from app.core.error_handlers import register_error_handlers
from app.core.health import health_router
from app.core.model_sync_checker import check_admin_model_sync
from app.shared.db.elasticsearch.indexes.initializer import ElasticIndexInitializer
from app.shared.db.qdrant.collections.intializer import QdrantCollectionInitializer
from app.shared.service.infrastructure.dishka.base import get_container
from app.shared.service.infrastructure.rabbitmq.connection import close_rabbitmq
from app.client.api.routers.user import user_router
from app.client.api.routers.token import jwt_router
from app.client.api.routers.ouath import oauth_router
from app.client.api.routers.pages import client_pages_router
from app.product.api.routers import book_router
from app.product.api.routers.review import book_review_router
from app.product.api.routers.pages import product_pages_router
from app.order.api.routers.cart import cart_router
from app.order.api.routers.wishlist import wishlist_router
from app.order.api.routers.order import order_router
from app.order.api.routers.pages import order_pages_router
from app.support.api.chat_router import support_router
from app.support.api.pages import support_pages_router
from app.agents.api.router import agent_router
from dishka.integrations.fastapi import setup_dishka
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    check_admin_model_sync(ADMIN_VIEWS)

    await taskiq_broker.startup()

    container = app.state.dishka_container

    async with container() as request_container:
        qdrant_collections = await request_container.get(
            QdrantCollectionInitializer,
        )
        await qdrant_collections.init()

        elastic_indexes = await request_container.get(
            ElasticIndexInitializer,
        )
        await elastic_indexes.init()

    # Первичное наполнение индексов (выполняется воркером).
    # Импорт здесь, а не на уровне модуля: задачи импортируют broker,
    # а broker импортирует модули задач — на уровне модуля был бы цикл.
    from app.product.service.infrastructure.taskiq.tasks.book.elastic_index import (
        elastic_index_books_task,
    )
    from app.product.service.infrastructure.taskiq.tasks.book.qdrant_index import (
        qdrant_index_books_task,
    )
    from app.support.infrastructure.taskiq.tasks.faq_index import faq_index_task

    await elastic_index_books_task.kiq()
    await qdrant_index_books_task.kiq()
    await faq_index_task.kiq()

    yield

    await app.state.dishka_container.close()
    await database.dispose()
    await close_redis()
    await close_rabbitmq()
    await taskiq_broker.shutdown()


def setup_routers(app: FastAPI) -> None:
    settings = get_settings()

    # health/ready — без префикса, чтобы LB/k8s опрашивали /health и /ready
    app.include_router(health_router)

    app.include_router(
        user_router,
        prefix=settings.api.prefix,
    )

    app.include_router(
        book_router,
        prefix=settings.api.prefix,
    )

    app.include_router(
        book_review_router,
        prefix=f"{settings.api.prefix}/books",
    )

    app.include_router(
        cart_router,
        prefix=f"{settings.api.prefix}/books",
    )

    app.include_router(
        wishlist_router,
        prefix=f"{settings.api.prefix}/books",
    ),

    app.include_router(
        order_router,
        prefix=settings.api.prefix,
    )

    app.include_router(
        support_router,
        prefix=settings.api.prefix,
    )

    app.include_router(
        agent_router,
        prefix=settings.api.prefix,
    )

    app.include_router(
        jwt_router,
        prefix=settings.api.prefix,
    )

    app.include_router(
        oauth_router,
        prefix=settings.api.prefix,
    )

    # html-страницы (по одному page-роутеру на контекст)
    app.include_router(template_router)
    app.include_router(product_pages_router)
    app.include_router(order_pages_router)
    app.include_router(client_pages_router)
    app.include_router(support_pages_router)


def setup_middlewares(app: FastAPI) -> None:
    import time
    import logging
    from fastapi import Request
    from starlette.middleware.sessions import SessionMiddleware
    from fastapi.middleware.cors import CORSMiddleware

    settings = get_settings()
    logger = logging.getLogger(settings.app.name)

    # session
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app.secret_key,
        max_age=60 * 60  # 1h
    )

    # cors
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # logging
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            "♦️ %s %s %.3f sec",
            request.method,
            request.url.path,
            process_time,
        )

        return response


def setup_static(app: FastAPI) -> None:
    static_path = Path("app/static")

    if static_path.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(static_path)), name="static"
        )


def create_app() -> FastAPI:
    setup_logging(),
    
    app = FastAPI(
        lifespan=lifespan,
        default_response_class=ORJSONResponse,
    )

    container = get_container()

    setup_dishka(container, app)
    setup_middlewares(app)
    setup_static(app)
    setup_routers(app)
    register_error_handlers(app)
    init_admin(
        app=app,
        templates_path=settings.app.templates_dir,
    )

    return app