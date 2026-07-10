from app.client.service.infrastructure.jwt.refresh_session import JWTRefreshAuthSession
from app.client.service.infrastructure.jwt.decode import jwt_decode

class UserLogoutUC:
    def __init__(
        self,
        jwt_refresh_session: JWTRefreshAuthSession,
    ):
        self.jwt_refresh_session = jwt_refresh_session
    
    async def from_device(self, refresh_token: str) -> None:
        payload = jwt_decode(refresh_token)
        
        await self.jwt_refresh_session.remove(
            user_id=payload.sub,
            jti=payload.jti,
        )

    async def from_all_devices(self, refresh_token: str) -> None:
        payload = jwt_decode(refresh_token)
        
        await self.jwt_refresh_session.remove_all_user_sessions(
            user_id=payload.sub
        )