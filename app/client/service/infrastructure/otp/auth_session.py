import uuid
from dataclasses import asdict
from app.client.dto.otp.base import OtpDTO
from app.core.config.base import Settings
from app.shared.service.infrastructure.base import json_to_dict, to_json
from app.shared.service.infrastructure.redis.clients import RedisClient
from typing import Optional, Union

class OtpAuthSession:
    def __init__(
        self,
        redis: RedisClient,
        settings: Settings,
    ):
        self.settings = settings
        self.redis = redis

    def _get_session_key(self, session_id: Union[str, uuid.UUID]) -> str:
        return f"{self.settings.otp.key}{str(session_id)}"

    def _get_email_key(self, email: str) -> str:
        return f"{self.settings.otp.key}{email}"

    async def get_by_owner(self, owner: str) -> Optional[OtpDTO]:
        email_key = self._get_email_key(owner)
        session_id = await self.redis.string.get(email_key)

        if not session_id:
            return None

        if isinstance(session_id, bytes):
            session_id = session_id.decode("utf-8")
        return await self.get(session_id)
        
    async def get(self, session_id: Union[str, uuid.UUID]) -> Optional[OtpDTO]:
        session_key = self._get_session_key(session_id)
        raw_data = await self.redis.string.get(session_key)

        if not raw_data:
            return None

        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode("utf-8")

        data = json_to_dict(raw_data) if isinstance(raw_data, str) else raw_data

        owner = data.get("owner")
        code = data.get("code")
        session_id = uuid.UUID(data.get("session_id"))

        if not code or not owner:
            return None

        ttl = await self.redis.key.ttl(session_key)

        return OtpDTO(
            owner=owner,
            code=code,
            session_id=session_id,
            ttl=ttl,
        )
        
    async def create(self, new_otp: OtpDTO) -> OtpDTO:
        session_key = self._get_session_key(new_otp.session_id)
        email_key = self._get_email_key(new_otp.owner)

        otp = to_json(asdict(new_otp), default=str)
        
        await self.redis.string.add(
            key=session_key,
            value=otp,
            ex=new_otp.ttl
        )
        
        await self.redis.string.add(
            key=email_key,
            value=str(new_otp.session_id),
            ex=new_otp.ttl
        )

        return new_otp

    async def delete(self, otp: OtpDTO) -> None:
        email_key = self._get_email_key(otp.owner)
        session_key = self._get_session_key(otp.session_id)
        await self.redis.key.remove(email_key, session_key)


def otp_generate_session_id():
    return uuid.uuid4()