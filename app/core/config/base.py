from functools import lru_cache
import os
from pathlib import Path
from pydantic import BaseModel, PostgresDsn
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)
from enum import Enum

BASE_DIR = Path(__file__).resolve().parents[3]


class Environment(str, Enum):
    DEV = "dev"
    PROD = "prod"
    TEST = "test"


class AppSettings(BaseModel):
    name: str
    host: str
    secret_key: str
    templates_dir: Path


class DBSettings(BaseModel):
    url: PostgresDsn
    echo: bool
    echo_pool: bool
    pool_size: int
    max_overflow: int
    limit: int
    

class TestDBSettings(BaseModel):
    url: PostgresDsn
    echo: bool = False


class ApiSettings(BaseModel):
    prefix: str


class AuthSettings(BaseModel):
    max_auth_user_sessions: int


class OtpSettings(BaseModel):
    ttl: int
    key: str
    length: int


class RabbitMQSettings(BaseModel):
    url: str
    

class CelerySettings(BaseModel):
    url: str
    
    
class SMTPSettings(BaseModel):
    dsn: str
    default_email: str
    no_reply_email: str


class RedisSettings(BaseModel):
    url: str


class AuthJWT(BaseModel):
    private_key_path: Path
    public_key_path: Path
    algorithm: str
    access_token_exp_minute: int
    refresh_token_exp_days: int
    
    type_field: str
    access_token_field: str
    refresh_token_field: str


class QDrantSettings(BaseModel):
    url: str


class ElasticsearchSettings(BaseModel):
    url: str


class OllamaSettings(BaseModel):
    url: str


class OauthGoogleSettings(BaseModel):
    client_id: str
    client_secret: str
    server_metadata: str


class LLMSettings(BaseModel):
    # big chat model (generation with tools)
    base_url: str
    api_key: str
    chat_model: str
    # small model: intent router + lightweight generation (offtopic).
    # Can live on its own provider (e.g. local Ollama); defaults to the main one.
    router_model: str
    router_base_url: str | None = None
    router_api_key: str | None = None
    # generation on the cheap provider (chitchat/offtopic replies).
    # A 3B classifier writes poor Russian — use a slightly bigger model here.
    # Defaults to router_model.
    small_chat_model: str | None = None


class StripeSettings(BaseModel):
    secret_key: str
    webhook_secret: str
    checkout_ttl_minutes: int = 30
    success_url: str = "http://127.0.0.1:8000/api/orders/success?order_id={order_id}"
    cancel_url: str = "http://127.0.0.1:8000/api/orders/cancel?order_id={order_id}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
        env_nested_delimiter="__",
        env_prefix="FASTAPI__",
        extra='ignore'
    )
    env: Environment = Environment.DEV
    app: AppSettings
    api: ApiSettings
    db: DBSettings
    auth: AuthSettings
    qdrant: QDrantSettings
    elasticsearch: ElasticsearchSettings
    test_db: TestDBSettings
    jwt: AuthJWT
    rabbitmq: RabbitMQSettings
    redis: RedisSettings
    otp: OtpSettings
    celery: CelerySettings
    smtp: SMTPSettings
    ollama: OllamaSettings
    oauth_google: OauthGoogleSettings
    llm: LLMSettings
    stripe: StripeSettings


@lru_cache
def get_settings() -> Settings:
    env = os.getenv("FASTAPI__ENV", "dev")
    env_file_map = {
        "dev": ".env.dev",
        "prod": ".env.prod",
        "test": ".env.test",
        "ci": ".env.ci",
    }
    env_file = BASE_DIR / env_file_map.get(env, ".env")

    return Settings(_env_file=env_file)