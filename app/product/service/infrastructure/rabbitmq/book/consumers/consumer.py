import asyncio
import logging
from app.shared.service.infrastructure.taskiq.broker import taskiq_broker
from app.product.service.infrastructure.rabbitmq.book.consumers.personal_reco import (
    start_consumer,
    _declare_topology,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    await taskiq_broker.startup()

    try:
        queue = await _declare_topology()

        while True:
            try:
                await start_consumer(queue)
            except Exception:
                logger.exception("Consumer crashed")
                await asyncio.sleep(5)
    finally:
        await taskiq_broker.shutdown()

if __name__ == "__main__":
    asyncio.run(main())