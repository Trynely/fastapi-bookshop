import json
import asyncio
import logging
from dishka import AsyncContainer
from app.core.config.support.rabbitmq.routing_keys import LLM_QUEUE
from app.core.container import create_dishka_container
from app.shared.service.infrastructure.rabbitmq.connection import get_rabbitmq_channel
from app.support.dto.events.user_msg import ChatUserMsgEVT
from app.support.usecase.bot_answer import BotAnswerUC

logger = logging.getLogger(__name__)

async def start_consumer(container: AsyncContainer):
    channel = await get_rabbitmq_channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(LLM_QUEUE, durable=True)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                # ошибка на одном сообщении не должна ронять consumer целиком
                try:
                    data = json.loads(message.body.decode())
                    event = ChatUserMsgEVT(**data)

                    async with container() as request_container:
                        chat_bot_answer = await request_container.get(BotAnswerUC)

                        await chat_bot_answer.generate(
                            user_message=event.message,
                            chat_id=event.chat_id,
                        )
                except Exception:
                    logger.exception("Failed to process LLM bot answer message")


async def main():
    container = create_dishka_container()

    try:
        await start_consumer(container)
    except Exception:
        logger.exception("Consumer crashed")
    finally:
        await container.close()

if __name__ == "__main__":
    asyncio.run(main())