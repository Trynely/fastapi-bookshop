from dataclasses import asdict
from typing import Any
from datetime import timedelta
from app.client.dto.jwt.access import JWTAccessTokenDTO
from app.client.dto.jwt.refresh import JWTRefreshTokenDTO
from app.core.config.base import get_settings
from app.client.service.infrastructure.jwt.encode import jwt_encode

settings = get_settings()

class JWTGenerator:
    @staticmethod
    def _create_jwt(
        token_type: str,
        data: dict[str, Any],
        expires_delta: timedelta
    ) -> str:
        payload = {settings.jwt.type_field: token_type, **data}
        
        return jwt_encode(
            payload=payload,
            exp_timedelta=expires_delta,
        )

    def access_token(
        self,
        token_data: JWTAccessTokenDTO,
        expires_minutes: int | None = None,
    ) -> str:
        minutes = expires_minutes or settings.jwt.access_token_exp_minute
        
        return self._create_jwt(
            token_type=settings.jwt.access_token_field,
            data=asdict(token_data),
            expires_delta=timedelta(minutes=minutes),
        )

    def refresh_token(
        self,
        token_data: JWTRefreshTokenDTO,
        expires_days: int | None = None,
    ) -> str:
        exp_days = expires_days or settings.jwt.refresh_token_exp_days

        return self._create_jwt(
            token_type=settings.jwt.refresh_token_field,
            data=asdict(token_data),
            expires_delta=timedelta(days=exp_days)
        )