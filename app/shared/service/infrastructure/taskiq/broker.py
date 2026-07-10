from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend
from app.core.config.base import get_settings

settings = get_settings()

taskiq_broker = AioPikaBroker(
    settings.rabbitmq.url,
    delayed_message_exchange_plugin=True,
).with_result_backend(RedisAsyncResultBackend(
    redis_url=settings.redis.url,
    result_ex_time=900,
))

scheduler = TaskiqScheduler(
    broker=taskiq_broker,
    sources=[LabelScheduleSource(taskiq_broker)],
)

import app.client.service.infrastructure.taskiq.tasks
import app.client.service.infrastructure.taskiq.schedules
from app.product.service.infrastructure.taskiq.tasks.book.qdrant_index import qdrant_index_books_task
from app.product.service.infrastructure.taskiq.tasks.book.elastic_index import elastic_index_books_task
from app.product.service.infrastructure.taskiq.tasks.book.update_popular_books import update_books_popularity
from app.order.service.infrastructure.taskiq.tasks.order.cancel_expired import cancel_expired_pending_orders