from functools import lru_cache
from app.core.config.base import get_settings

settings = get_settings()

@lru_cache
def load_private_key() -> str:
    return settings.jwt.private_key_path.read_text()


@lru_cache
def load_public_key() -> str:
    return settings.jwt.public_key_path.read_text()