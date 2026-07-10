import time
from app.core.config.base import get_settings
from app.shared.service.infrastructure.redis.clients import RedisClient
from app.core.config.client.jwt.refresh_session_time import jwt_refresh_user_session_conf, jwt_refresh_user_sessions_conf

class JWTRefreshAuthSession:
    def __init__(
        self,
        redis_connection: RedisClient,
    ):
        self._redis = redis_connection
        self.settings = get_settings()

    async def create(
        self,
        user_id: int,
        jti: str,
        ttl: int,
    ):
        sessions_key = jwt_refresh_user_sessions_conf(user_id)
        sessions_count = await self._redis.sorted_set.count(
            sessions_key
        )

        if sessions_count >= self.settings.auth.max_auth_user_sessions:
            oldest_session = await self._redis.sorted_set.range(
                key=sessions_key,
                start=0,
                stop=0,
            )

            if oldest_session:
                oldest_jti = oldest_session[0]

                if isinstance(oldest_jti, bytes):
                    oldest_jti = oldest_jti.decode()
                
                await self.remove(
                    user_id=user_id,
                    jti=oldest_jti,
                )

        await self._redis.string.add(
            key=jwt_refresh_user_session_conf(jti),
            value=user_id,
            ex=ttl,
        )

        await self._redis.sorted_set.add(
            key=sessions_key,
            mapping={jti: time.time()},
        )

        await self._redis.key.expire(
            key=sessions_key,
            ttl=ttl,
        )

    async def is_exists(self, jti: str) -> bool:
        return await self._redis.key.exists(
            jwt_refresh_user_session_conf(jti)
        )

    async def remove(self, user_id: int, jti: str):
        await self._redis.key.remove(jwt_refresh_user_session_conf(jti))
        await self._redis.sorted_set.remove(
            jwt_refresh_user_sessions_conf(user_id),
            jti,
        )

    async def remove_all_user_sessions(self, user_id: int):
        sessions_key = jwt_refresh_user_sessions_conf(user_id)

        jtis = await self._redis.sorted_set.range(
            sessions_key,
            0,
            -1,
        )
        
        if not jtis:
            return

        jwt_refresh_keys = [
            jwt_refresh_user_session_conf(
                jti.decode() if isinstance(jti, bytes) else jti
            )
            for jti in jtis
        ]

        await self._redis.key.remove(*jwt_refresh_keys)
        await self._redis.key.remove(sessions_key)