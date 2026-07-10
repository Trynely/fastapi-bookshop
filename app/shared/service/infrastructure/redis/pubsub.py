import redis.asyncio as redis
from app.shared.service.infrastructure.base import to_json
from typing import Union

class RedisPubsub:
    def __init__(self, redis_connection: redis.Redis):
        self.redis = redis_connection

    async def publish(self, channel: str, payload: Union[dict, str]) -> None:
        data = payload if isinstance(payload, str) else to_json(payload)
        await self.redis.publish(channel, data)

    async def subscribe(self, *channels: str):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(*channels)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {
                        "channel": message["channel"],
                        "data": message["data"]
                    }
        finally:
            await pubsub.unsubscribe(*channels)
            await pubsub.close()