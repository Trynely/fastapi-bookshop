import redis.asyncio as redis

class BaseRedisClient:
    def __init__(self, redis_connection: redis.Redis):
        self.redis = redis_connection